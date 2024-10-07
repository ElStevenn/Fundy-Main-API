import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Tuple

from app.founding_rate_service.bitget_layer import BitgetClient

class FundingRateChart:
    """
    A class to analyze volatility changes around funding rate expiration times for a given trading symbol.

    Attributes:
    - symbol (str): The trading symbol to analyze.
    - granularity (str): The granularity of the candlestick data (default '1min').
    - limit (int): The number of data points to fetch (default 1000).
    - df (DataFrame): The fetched candlestick data.
    - latest_funding_time (str): The latest funding rate expiration time.
    """

    def __init__(self, symbol: str, granularity: str = '1min', limit: int = 1000):
        self.symbol = symbol
        self.granularity = granularity
        self.limit = limit
        self.candle_data = BitgetClient()
        self.df = None
        self.latest_funding_time = None
        self.latests_founing_rates = []

    async def fetch_data(self):
        """
        Fetch candlestick and funding rate data asynchronously.
        """
        # Fetch candlestick data and funding rate data concurrently
        candlestick_task = self.candle_data.get_candlestick_chart(self.symbol, granularity=self.granularity, limit=self.limit)
        funding_rate_task = self.candle_data.get_historical_funding_rate(self.symbol)
        
        # Gather results from both tasks
        result, funding_rates = await asyncio.gather(candlestick_task, funding_rate_task)

        # Process candlestick data
        if result.size > 0:
            df = pd.DataFrame(result, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Timestamp'] = pd.to_datetime(df['Timestamp'].astype(float), unit='s', utc=True)
            df.set_index('Timestamp', inplace=True)
            df.dropna(inplace=True)  # Ensure no NaN values in the DataFrame
            self.df = df  # Store for further analysis
        else:
            print("No candlestick data fetched. Please check the symbol and granularity.")
            df = None

        # Ensure funding rates are in a compatible format
        if funding_rates:
            # Convert funding rates from list of tuples to list of dictionaries for easier handling
            funding_rates = [{'fundingRateTimes100': rate[0], 'fundingTimeEurope': rate[1]} for rate in funding_rates]
        else:
            print("No funding rate data fetched.")
            funding_rates = None

        return df, funding_rates


    async def fetch_funding_rate_expiration_time(self):
        """
        Fetch the latest funding rate expiration time.
        """
        _, funding_rates = await self.fetch_data()

        if funding_rates:
            for funding_rate in funding_rates:
                funding_time_str = funding_rate['fundingTimeEurope']  
                funding_time_utc = datetime.fromisoformat(funding_time_str).astimezone(timezone.utc)
                self.latests_founing_rates.append(funding_time_utc.strftime('%Y-%m-%d %H:%M:%S%z'))


            self.latest_funding_time = max(funding_rates, key=lambda x: datetime.fromisoformat(x['fundingTimeEurope']).timestamp())['fundingTimeEurope']
            self.timestamp_value = datetime.fromisoformat(self.latest_funding_time).strftime('%Y-%m-%d %H:%M:%S%z')

            return self.latest_funding_time, self.latests_founing_rates
        else:
            print("No funding rate data fetched.")
            return None


    def analyze_last_volatility(self, period: int = 1) -> Tuple[float, pd.DataFrame]:

        """
        Analyze the last volatility change starting 1 minute before and ending 5 minutes after
        the funding rate expiration time and return an integer value. Get this from the last founding rate. Pending to be tested
        """
        if period < 1:
            print("Period not valid, either 1 or more than 1")
            return None, None


        if not self.latests_founing_rates:
            print("Suddently founding rate is not avariable.")
            return None, None
        
        # Convert funding time to datetime
        funding_time = pd.to_datetime(self.latests_founing_rates[period - 1], utc=True)

        # Ensure data is fetched
        if self.df is None or self.df.empty:
            print("Candlestick data is not available.")
            return None, None

        # Define the start and end time within the period
        start_time = funding_time - pd.Timedelta(minutes=1)
        end_time = funding_time + pd.Timedelta(minutes=10)

        # Filter the data within the defined period
        period_data = self.df[(self.df.index >= start_time) & (self.df.index <= end_time)]
        
        # Debugging statement to ensure correct filtering
        print(f"Filtered Data for Volatility Calculation of period {period}: \n{period_data}")

        if not period_data.empty:
            # Calculate the volatility as the percentage change in the 'Close' prices
            price_start = period_data['Open'].iloc[0]
            price_end = period_data['Low'].min()
            # volatility = ((price_end - price_start) / price_start) * 100

            if price_start > price_end:

                volatility = ((price_end - price_start) / price_start) * 100
            else:
                volatility = (price_start / price_end) * 100

      
            volatility_int = float(volatility)

            print(f"Volatility Change between {start_time} and {end_time}: {volatility_int}%")

            # Determine if the volatility went up or down
            if volatility > 0:
                print("Volatility increased after the funding rate expiration.")
            else:
                print("Volatility remained unchanged or decreased after the funding rate expiration.")

            return volatility_int, period_data
        else:
            print("No data available to calculate the last volatility.")


    async def analyze_incrementation(self) -> dict:
        """
        Analyse the incrementation over the last 8 hours and make sure that 1 hour ago the ATH hasn't been superated by 5%,
        if the ATH in this range of time has been superated for over 15% mark this as enter short
        """
        # Function constants
        min_persentage = 10.0
        min_persentage_short_term = 5.0

        # Check if DataFrame is available
        if self.df is None or self.df.empty:
            return {}
        
        # Get whole incrementation over the last 8 hours (8 * 60 minutes)
        start_price = self.df['Open'].iloc[0]
        end_price = self.df['Close'].iloc[-1]
        highest_value = self.df['High'].max()


        if start_price > end_price:
            volatility = ((end_price - start_price) / start_price) * 100
        else:
            volatility = ((start_price - end_price) / end_price) * 100    

        print("Volatility result -> ", volatility)

        # Calculate volatility from the highest value of the period of time
        volatility_from_highest = ((end_price - highest_value) / highest_value) * 100
        print("Volatility from highest -> ", volatility_from_highest)
        
        # Calculate volatility from the highest price of 2 hours ago (120 minutes)
        df_2h_ago = self.df.tail(120)
        df1_highest_value = df_2h_ago['High'].max()
        two_hours_volatility = ((end_price - df1_highest_value) / df1_highest_value) * 100
        print("two volatility -> ", two_hours_volatility)

        
        if volatility > min_persentage: # The price is generally going up

            if two_hours_volatility >= min_persentage_short_term:
                if volatility_from_highest < min_persentage_short_term + 5:
                    print("Continue, likely will be in other exceptions")
                else:
                    # Open long but a little bit risky
                    return {"result": True, "side": "long", "risky": True, "chart": "not avariable", "type": "normal"}
            else:
                # Open long
                return {"result": True, "side": "long", "risky": False, "chart": "not avariable", "type": "normal"}
        
        # Calculate short positions
        if volatility_from_highest <= -15:
            # Enter short
            return {"result": True, "side": "short", "risky": False, "chart": "1.1", "type": "after"} 

        df_1h_ago = self.df.tail(60); df_1h_ago_highest_value = df_1h_ago['High'].max()
        if highest_value == df_1h_ago_highest_value: 
            
            # Calculate volatility from max value to last value     
            hour_volatility = ((end_price - df_1h_ago_highest_value) / df_1h_ago_highest_value) * 100
            if hour_volatility < 1.3:
                return {"result": True, "side": "long", "risky": False, "chart": "1.2", "type": "normal"} 
            
            if hour_volatility > 7.0:
                return {"result": True, "side": "short", "risky": True, "chart": "1.4", "type": "after"}

        # View incrementation of last 2 days (42h)
        self.granularity = "15min"; self.limit = 4 * 42
        await self.fetch_data()

        start_price_2d = self.df['Open'].iloc[0]
        higest_price_2d_lst_hr = self.df['High'].tail(60).max()

        if start_price_2d > higest_price_2d_lst_hr:
            volatility = ((higest_price_2d_lst_hr - start_price_2d) / start_price_2d) * 100
        else:
            volatility = (start_price_2d / higest_price_2d_lst_hr) * 100

        print("loco volatility -> ", volatility)
        if volatility > 15:
            # Analyze setback
            last_price = self.df['Close'].iloc[-1]
            two_hour_higest_price = self.df['High'].tail(4 * 2).max()

            setback = ((last_price - two_hour_higest_price) / two_hour_higest_price) * 100
            print("setback -> ",setback)

            if setback < -5: # Chacke min setback if you see it to low
                return {"result": True, "side": "short", "risky": True, "chart": "1.6", "type": "after-variation"}
            else:
                return {"result": True, "side": "long", "risky": True, "chart": "1.5", "type": "after"}

        elif volatility < -15:
            return {"result": True, "side": "long", "risky": True, "chart": "1.7", "type": "normal"}


        # No clear signal
        return {"result": False, "side": None}


    def determine_by_past_funding_rates(self):
        """
        structure 2.1 | If the last founing rate the prices was going down, the prediction will be True as open short however with risky True. Meanwhile the
        2 past prices were going down, the risky is False and should Enter into the operation 
        """

        last, _ = self.analyze_last_volatility(period=1)
        pre_last, _ = self.analyze_last_volatility(period=2)

        if last < -1.5:
            if last >= pre_last or pre_last < -1.5:
                return {"result": True, "side": "long", "risky": False, "chart": "2.1", "type": "after"} # Low risk variation

            else:
                return {"result": True, "side": "long", "risky": True, "chart": "2.1", "type": "after"} # Hight rick variation

        return {"result": False, "side": None}

    async def analyse_period_founing_rate(self, symbol, period_dateiso: str, period_unix_timetamp: float, short_period = 10) -> dict:
        # Debuging delete this
        print(f"There was a founing rate {period_dateiso} in period")

        # 8 Hours Variation since founding rate
        cdle_8h = await self.candle_data.get_candlestick_chart(symbol=symbol, granularity='15min', limit=(60 * 8) * 2)

        if cdle_8h.size < 0:
            return {}
        

        # Get 8h period as 15min chart
        df_8h = pd.DataFrame(cdle_8h, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df_8h['Timestamp_iso'] = pd.to_datetime(df_8h['Timestamp'], unit='s', utc=True).dt.tz_convert('Europe/Amsterdam')

        # Fetch needed period 
        start_time = datetime.fromisoformat(period_dateiso)
        end_time = start_time + timedelta(hours=8)
        filtered_df = df_8h.loc[(df_8h['Timestamp_iso'] >= start_time) & (df_8h['Timestamp_iso'] <= end_time)]

        # Select needed values
        start_price = df_8h.loc[df_8h['Timestamp_iso'] == start_time, 'Open'].values[0]
        lowest_price_range = filtered_df['Low'].min()
        higest_price_range = filtered_df['High'].max()
        end_price = filtered_df['Close'].iloc[-1]
        
        # Get 8h total  variation
        total_vol_8h = ((end_price - start_price) / start_price) * 100

        # Get Regression
        regression_val = ((lowest_price_range - start_price) / start_price) * 100


        # Get progresive
        if start_price < higest_price_range:
            progresive_var = ((higest_price_range - start_price) / start_price) * 100


        # 10 Minutes Variation since founding rate to lowest price or higest price / depending
        # Debugging
        print(f"There was a founding rate {period_dateiso} in period")

        # 10 Minutes Variation since founding rate to lowest price or highest price / depending
        # The given period_unix_timetamp should already be in seconds (like 1725788700.0), so we work with it directly.
        dt = datetime.fromtimestamp(period_unix_timetamp, tz=timezone.utc)

        # Subtract 1 minute and add 10 minutes in seconds
        start_time10 = dt - timedelta(minutes=1)
        end_timeX = dt + timedelta(minutes=short_period)

        # Convert both times to Unix timestamps in **seconds**
        start_time10_sec = start_time10.timestamp()
        end_timeX_sec = end_timeX.timestamp()

        # Print the calculated values in seconds for debugging
        print(f"Start time (sec): {start_time10_sec}, End time (sec): {end_timeX_sec}")

        # Convert the timestamps to milliseconds before calling the API
        start_time10_ms = int(start_time10_sec * 1000)
        end_timeX_ms = int(end_timeX_sec * 1000)

        # Print the calculated values in milliseconds for further debugging
        print(f"Start time (ms): {start_time10_ms}, End time (ms): {end_timeX_ms}")

        # Call the API with the correct values
        cdle_X_min = await self.candle_data.get_1min_candlestick_chart(symbol=symbol, startTime=start_time10_ms, endTime=end_timeX_ms)

        print(f"API Response: {cdle_X_min}")

        """
        # Get Needed     
        df_Xmin = pd.DataFrame(cdle_X_min, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df_Xmin['Timestamp_iso'] = pd.to_datetime(df_8h['Timestamp'], unit='s', utc=True).dt.tz_convert('Europe/Amsterdam')

        # Fetch data of this period
        print(df_Xmin)


        print(f"{short_period} min result -> ", cdle_X_min)
        """

        return {
            "8h_period_analysis": {
                "total_vor_8h": total_vol_8h, 
                "regression_var": regression_val,
                "progresive_var": progresive_var
                },
            f"{cdle_X_min}min_period_analysis": {
                "total_var_{cdle_X_min}m": "",
                "regression_var" : ""
            }
        }

    async def get_historical_analysis(self):
        founding_rates = await self.candle_data.get_historical_funding_rate(self.symbol)
        min_to_analysis = -0.5

        result = []
        for i, period in enumerate(reversed(founding_rates)):
            if period[0] < min_to_analysis:
                # Analyse period
                historical_analysis = await self.analyse_period_founing_rate(symbol=self.symbol, period_dateiso=str(period[1]), period_unix_timetamp=float(period[0]))
                result.append(historical_analysis)
            
        return result



async def main_testings():
    # Example of every single analysis and determine possition

    periods = 2
    limit = (60 * 8) * periods 

    chart = FundingRateChart("UXLINKUSDT", granularity='1min', limit=limit) 

    await chart.fetch_data()
    await chart.fetch_funding_rate_expiration_time() #

    

    # Analyse incrementation 
    past_founing_rate = await chart.get_historical_analysis()

    print("last incrementation -> ", past_founing_rate)


if __name__ == "__main__":
    asyncio.run(main_testings())