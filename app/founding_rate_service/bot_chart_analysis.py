# bot_chart_analysis.py
# Author: Pau Mateu
# Email: paumat17@gmail.com

import pandas as pd
import numpy as np
from typing import Literal
from datetime import datetime
from scipy.signal import argrelextrema
import pytz, asyncio

from app.founding_rate_service.bitget_layer import BitgetClient


class BotChartAnalysis():
    """
    Analysis if funding rate is more than 1.3
    """
    def __init__(self, symbol: str, current_funding_rate: float, last_fr_exec_time: int):
        self.symbol = symbol
        self.current_funding_rate = current_funding_rate
        self.last_fr_exec_time = last_fr_exec_time
        self.volatility_weight = None
        self.bitget_service = BitgetClient()
        self.api_timezone = pytz.utc

    async def get_whole_analysis(self):
        """
        Performs the complete analysis by fetching volatility weight and weekly analysis.
        """
        self.volatility_weight = await self.get_volatility_weight()

        # Get weekly analysis
        weekly_analysis = await self.get_weekly_analysis()
        # Get daily analysis
        daily_analysis = await self.get_daily_analysis()

        # Combine analyses
        whole_analysis = {
            **weekly_analysis,
            **daily_analysis,
        }

        return whole_analysis

    async def make_decision(self):
        """From the given result, make a decision based on the past, whether to open long or short in that position"""
        pass

    async def get_volatility_weight(self):
        bitcoin_marketcap = await self.bitget_service.get_market_cap('BTCUSDT')
        crypto_marketcap = await self.bitget_service.get_market_cap(self.symbol)

        # Calculate the logarithmic volatility weight
        volatility_weight = np.log(crypto_marketcap) / np.log(bitcoin_marketcap)

        return volatility_weight

    async def get_needed_df(self, period: Literal['weekly', 'daily', '8h', '10m', '1m']) -> pd.DataFrame:
        """Get DataFrame during the specified period."""
        current_time = int(datetime.now(pytz.utc).timestamp() * 1000)
        if period == '10m':
            granularity = '1min'
            starting_time = self.last_fr_exec_time - (1 * 60 * 1000)
            end_time = self.last_fr_exec_time + (10 * 60 * 10000)
        elif period == '1m':
            granularity = '1min'
            starting_time = self.last_fr_exec_time - (1 * 60 * 1000)
            end_time = self.last_fr_exec_time + (1 * 60 * 1000)
        elif period == '8h':
            granularity = '15m'
            starting_time = self.last_fr_exec_time
            end_time = current_time
        elif period == 'daily':
            granularity = '15m'  # Using 15-minute intervals for more data points
            starting_time = current_time - (24 * 60 * 60 * 1000)
            end_time = current_time
        elif period == 'weekly':
            granularity = '1H'
            starting_time = current_time - (7 * 24 * 60 * 60 * 1000)
            end_time = current_time

        # Get Chart and turn it into a DataFrame
        needed_chart = await self.bitget_service.get_candlestick_chart(
            self.symbol, granularity, start_time=starting_time, end_time=end_time
        )

        df = pd.DataFrame(needed_chart, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'National_Value'])

        df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
        df['Open'] = pd.to_numeric(df['Open'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
        df.set_index('Timestamp', inplace=True)

        # Simple Moving Average (20)
        df['SMA_20'] = df['Close'].rolling(window=20).mean()

        # Relative Strength Index (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))

        # Moving Average Convergence Divergence (MACD)
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # Bollinger Bands (20, 2)
        df['Middle_Band'] = df['Close'].rolling(window=20).mean()
        df['Upper_Band'] = df['Middle_Band'] + (df['Close'].rolling(window=20).std() * 2)
        df['Lower_Band'] = df['Middle_Band'] - (df['Close'].rolling(window=20).std() * 2)

        return df

    def find_local_extrema(self, series, order=5):
        """Find local maxima and minima in a pandas Series using scipy's argrelextrema."""
        n = order  # number of points to be checked before and after

        # Local maxima
        max_idx = argrelextrema(series.values, np.greater_equal, order=n)[0]
        # Local minima
        min_idx = argrelextrema(series.values, np.less_equal, order=n)[0]

        return max_idx, min_idx

    def identify_trend(self, highs_values, lows_values):
        """
        Identify trend based on sequences of highs and lows.
        """
        # Ensure that highs and lows are sorted by time
        highs_values = highs_values.sort_index()
        lows_values = lows_values.sort_index()

        # Check if we have at least two highs and lows
        if len(highs_values) >= 2 and len(lows_values) >= 2:
            # Get the last two highs and lows
            recent_highs = highs_values['Close'].iloc[-2:]
            recent_lows = lows_values['Close'].iloc[-2:]

            # Check for higher highs and higher lows
            if recent_highs.iloc[-1] > recent_highs.iloc[-2] and recent_lows.iloc[-1] > recent_lows.iloc[-2]:
                return 'bullish'
            # Check for lower highs and lower lows
            elif recent_highs.iloc[-1] < recent_highs.iloc[-2] and recent_lows.iloc[-1] < recent_lows.iloc[-2]:
                return 'bearish'
            else:
                return 'neutral'
        else:
            return 'neutral'

    async def get_weekly_analysis(self):
        """
        From a given chart of 1H from the last week, get the following data:
        - weekly_trend: Literal["bullish", "bearish", "neutral"]
        - weekly_volatility_index: float
        - average_trading_volume: float
        - variation: float
        - trendline_slope_lows: float
        - trendline_slope_highs: float
        - weekly_trendline: Literal["uptrend", "downtrend", "sideways"]
        """
        df = await self.get_needed_df('weekly')

        # Handle exceptions
        if df.empty:
            raise ValueError("DataFrame is empty. Check data fetching logic.")

        if not pd.api.types.is_numeric_dtype(df['Close']) or not pd.api.types.is_numeric_dtype(df['Volume']):
            raise TypeError("'Close' and 'Volume' columns must be numeric.")

        # Calculate Volatility Index
        df['Log_Returns'] = np.log(df['Close'] / df['Close'].shift(1))
        weekly_volatility_index = df['Log_Returns'].std() * np.sqrt(24)

        # Average trading volume and variation
        average_trading_volume = df['Volume'].mean()
        variation = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100

        # Trendline Analysis
        # Find local maxima and minima
        high_indices, low_indices = self.find_local_extrema(df['Close'], order=3)

        # Convert timestamps to numerical values
        timestamps = df.index.astype(np.int64) // 10**9

        # Fit trendlines
        slope_lows, slope_highs = None, None

        if len(low_indices) >= 2:
            x_lows = timestamps[low_indices]
            y_lows = df['Close'].iloc[low_indices].values
            slope_lows, _ = np.polyfit(x_lows, y_lows, 1)

        if len(high_indices) >= 2:
            x_highs = timestamps[high_indices]
            y_highs = df['Close'].iloc[high_indices].values
            slope_highs, _ = np.polyfit(x_highs, y_highs, 1)

        # Determine Weekly Trendline
        if slope_lows is not None and slope_highs is not None:
            if slope_lows > 0 and slope_highs > 0:
                weekly_trendline = 'uptrend'
            elif slope_lows < 0 and slope_highs < 0:
                weekly_trendline = 'downtrend'
            else:
                weekly_trendline = 'sideways'
        else:
            weekly_trendline = 'sideways'

        # Identify trend based on highs and lows
        highs = df.iloc[high_indices][['Close']]
        lows = df.iloc[low_indices][['Close']]
        weekly_trend = self.identify_trend(highs, lows)

        return {
            "weekly_trend": weekly_trend,
            "weekly_volatility_index": round(weekly_volatility_index, 2),
            "average_trading_volume": round(average_trading_volume, 2),
            "variation": round(variation, 2),
            "trendline_slope_lows": slope_lows if slope_lows is not None else 0,
            "trendline_slope_highs": slope_highs if slope_highs is not None else 0,
            "weekly_trendline": weekly_trendline
        }

    async def get_daily_analysis(self):
        """
        From a given chart of 1D of 15min get:
        - daily_trend: Literal["bullish", "bearish", "neutral"]
        - daily_variation_index: float
        - average_trading_volume: float
        """
        df = await self.get_needed_df('daily')

        # Handle exceptions
        if df.empty:
            raise ValueError("DataFrame is empty. Check data fetching logic.")

        if not pd.api.types.is_numeric_dtype(df['Close']) or not pd.api.types.is_numeric_dtype(df['Volume']):
            raise TypeError("'Close' and 'Volume' columns must be numeric.")

        # Calculate variation index
        variation = ((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0]) * 100

        # Average trading volume
        average_trading_volume = df['Volume'].mean()

        # Trendline Analysis
        # Find local maxima and minima
        high_indices, low_indices = self.find_local_extrema(df['Close'], order=5)

        # Convert timestamps to numerical values
        timestamps = df.index.astype(np.int64) // 10**9

        # Fit trendlines
        slope_lows, slope_highs = None, None

        if len(low_indices) >= 2:
            x_lows = timestamps[low_indices]
            y_lows = df['Close'].iloc[low_indices].values
            slope_lows, _ = np.polyfit(x_lows, y_lows, 1)

        if len(high_indices) >= 2:
            x_highs = timestamps[high_indices]
            y_highs = df['Close'].iloc[high_indices].values
            slope_highs, _ = np.polyfit(x_highs, y_highs, 1)

        # Identify trend based on highs and lows
        highs = df.iloc[high_indices][['Close']]
        lows = df.iloc[low_indices][['Close']]
        daily_trend = self.identify_trend(highs, lows)

        # If the variation is significantly positive, adjust the trend to 'bullish' if it's neutral
        if variation > 2 and daily_trend == 'neutral':
            daily_trend = 'bullish'

        return {
            'daily_trend': daily_trend,
            'daily_variation_index': round(variation, 2),
            'average_trading_volume': round(average_trading_volume, 2),
        }


    async def get_8h_varition(self):
        """I only need the diff and regression since funding rate expired"""
        pass

    async def get_10m_variation(self):
        """See what happened over the last 2 funding rates with the chart, whether was down or nothing happened, also i'll need to get the last and pre-last funding rate just in case"""
        pass

    async def get_1m_variation(self):
        """See what happened over the last 2 funding rate with the chart, 1 min analysis, whether was down or nothing happening during that minute. I'll need to get the last and pre-last funding rate value to evaluate a result"""
        pass



async def main_testing():
    eight_hours_ago = int(datetime.now(pytz.utc).timestamp() * 1000) - (8 * 60 * 60 * 1000)
    chart_analysis = BotChartAnalysis('MOODENGUSDT', -0.5, eight_hours_ago)

    res = await chart_analysis.get_weekly_analysis()
    # res = await chart_analysis.get_needed_df('weekly')
    # res = await chart_analysis.get_daily_analysis()
    print(res)

if __name__ == "__main__":
    asyncio.run(main_testing())