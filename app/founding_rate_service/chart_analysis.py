import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone
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

        if result.size > 0:
            # Create DataFrame from candlestick data
            df = pd.DataFrame(result, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['Timestamp'] = pd.to_datetime(df['Timestamp'].astype(float), unit='s', utc=True)
            df.set_index('Timestamp', inplace=True)
            df.dropna(inplace=True)  # Ensure no NaN values in the DataFrame
            self.df = df  # Store for further analysis
            return df, funding_rates
        else:
            print("No candlestick data fetched. Please check the symbol and granularity.")
            return None, None

    async def fetch_funing_rate_expiration_time(self):
        """
        Fetch the latest funding rate expiration time.
        """
        _, funding_rates = await self.fetch_data()

        print("funing rates -> ",funding_rates)
        
        if funding_rates:
            # Get all the datetimes as timestamp
            for founding_rate in funding_rates:
                self.latests_founing_rates.append(datetime.fromtimestamp(int(founding_rate['fundingTime']) / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S%z'))

            self.latest_funding_time = max(funding_rates, key=lambda x: x['fundingTime'])['fundingTime']
            self.timestamp_value = datetime.fromtimestamp(int(self.latest_funding_time) / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S%z')

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
            print("Candlestick data is not available.")
            return
        
        # Get whole incrementation over the last 8 hours (8 * 60 minutes)
        start_price = self.df['Open'].iloc[0]; print(self.df)
        print("Start price -> ", start_price)
        end_price = self.df['Close'].iloc[-1]
        print("End price -> ", end_price)
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

    def determine_by_past_founing_rates(self):
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


async def main_testings():
    # Example of every single analysis and determine possition

    periods = 2
    limit = (60 * 8) * periods 

    chart = FundingRateChart("UXLINKUSDT", granularity='1min', limit=limit)# Limit is equal to 3 periods 

    await chart.fetch_data() # Important call this method after calling the previous one
    await chart.fetch_funing_rate_expiration_time() # Call this method if expiration time with other times is involved

    

    # Analyse incrementation 
    past_founing_rate = chart.determine_by_past_founing_rates()

    print("last incrementation -> ", past_founing_rate)


if __name__ == "__main__":
    asyncio.run(main_testings())