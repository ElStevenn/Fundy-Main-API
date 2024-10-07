from config import BITGET_APIKEY, BITGET_PASSPHRASE, BITGET_SECRET_KEY, LEVERAGE, COINMARKETCAP_APIKEY
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException
from typing import Optional, Literal
from datetime import datetime, timedelta
from datetime import timezone as dttimezone
from zoneinfo import ZoneInfo
import pandas as pd
from pytz import timezone
import asyncio
import aiohttp
import hmac
import base64
import json
import time
import numpy as np
import pytz


# Define all possible granularity values
Granularity = Literal[
    '1min', '5min', '15min', '30min', 
    '1h', '4h', '6h', '12h',          
    '1day', '3day',                   
    '1week',                           
    '1M',                             
    '6Hutc', '12Hutc', '1Dutc', '3Dutc', '1Wutc', '1Mutc' 
]



class BitgetClient:
    def __init__(self):
        self.apikey = BITGET_APIKEY
        self.api_secret_key = BITGET_SECRET_KEY
        self.passphrase = BITGET_PASSPHRASE
        self.api_url = "https://api.bitget.com"
        self._api_timezone = pytz.utc


    def get_timestamp(self) -> str:
        # Generate timestamp in milliseconds
        return str(int(time.time() * 1000))

    def generate_signature(self, message: str) -> str:
        mac = hmac.new(bytes(str(self.api_secret_key), encoding='utf8'), bytes(str(message), encoding='utf-8'), digestmod='sha256')
        return base64.b64encode(mac.digest()).decode()

    def get_headers(self, method: str, request_path: str, query_string: str, body: str) -> dict:
        timestamp = self.get_timestamp()
        
        # Construct the prehash string according to the presence of query_string
        if query_string:
            prehash_string = f"{timestamp}{method.upper()}{request_path}?{query_string}{body}"
        else:
            prehash_string = f"{timestamp}{method.upper()}{request_path}{body}"

        sign = self.generate_signature(prehash_string)

        # Ensure all headers are non-None and strings
        return {
            "Content-Type": "application/json",
            "ACCESS-KEY": str(self.apikey) if self.apikey else "",
            "ACCESS-SIGN": str(sign) if sign else "",
            "ACCESS-PASSPHRASE": str(self.passphrase) if self.passphrase else "",
            "ACCESS-TIMESTAMP": timestamp,
            "locale": "en-US"
        }



    async def get_future_cryptos(self):
        method = "GET"
        request_path = "/api/v2/mix/market/tickers"
        params = {
            "productType": "USDT-FUTURES"
        }

        query_string = '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
        url = f"{self.api_url}{request_path}?{query_string}"
        headers = self.get_headers(method, request_path, query_string, "")

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                return data

    def fetch_future_cryptos(self, dict_data: dict):
        data = dict_data["data"]
        sorted_data = [{"symbol": d["symbol"], "fundingRate": float(d["fundingRate"]) * 100} for d in sorted(data, key=lambda x: float(x["fundingRate"]))]
        return sorted_data

    async def open_order(self, symbol: str, amount: str, mode: Literal['short', 'long'] = 'Buy', price: Optional[str] = None):
        print(f"Opening order: {symbol}")
        url = "http://3.141.197.183:8000/open_order_futures_normal"
        headers = {
            "password": "mierda69",
            "Content-Type": "application/json"  
        }
        data = {
            "symbol": symbol,
            "mode": mode,
            "amount_usdt": amount,  
            "leverage": LEVERAGE
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                content_type = response.headers.get('Content-Type')
                if content_type and 'application/json' in content_type:
                    data = await response.json()
                else:
                    data = await response.text()  
                return data


    async def close_order(self, symbol):
        print(f"Closing order: {symbol}")
        url = f"http://3.141.197.183:8000/close_order/{symbol}"
        headers = {
            "password": "mierda69",
            "Content-Type": "application/json"  
        }
        data = {
            "price": 0
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                content_type = response.headers.get('Content-Type')
                if content_type and 'application/json' in content_type:
                    data = await response.json()
                else:
                    data = await response.text()
                    if data == 'Internal Server Error':
                        raise HTTPException(status_code=400, detail=f"Internal server error while closing the operation: {data}")
                return data

    async def get_pnl_order(self, symbol):
        print("Trying to get the last order values")
        url = f"http://3.141.197.183:8000/get_historical_possition/{symbol}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content_type = response.headers.get('Content-Type')
                if content_type and 'application/json' in content_type:
                    data = await response.json()
                else:
                    data = await response.text()
                    if data == 'Internal Server Error':
                        raise HTTPException(status_code=400, detail=f"Internal server error while closing the operation: {data}")
                result =  data["data"]["list"][0]
           
                # Fetch Data
                last_pnl_order = {
                    "id": result.get('positionId'),
                    "symbol": result.get('symbol'),
                    "operation_datetime": datetime.fromtimestamp(int(result.get('utime', 0)) / 1000, tz=ZoneInfo('UTC')).astimezone(ZoneInfo('Europe/Amsterdam')).isoformat() if result.get('utime') else None,
                    "pnl": result.get('pnl'),
                    "avg_entry_price": result.get('openAvgPrice'),
                    "side": result.get('holdSide'),
                    "closed_value": result.get('closeAvgPrice'),
                    "opening_fee": result.get('openFee'),
                    "closing_fee": result.get('closeFee'),
                    "net_profits": result.get('netProfit')
                }
                
                return last_pnl_order

    def calculate_api_calls(self, start_time: int, end_time: int, granularity_ms: int):
        time_diff = end_time - start_time
        total_candles = time_diff // granularity_ms
        max_candles_per_call = 1000

        print(f"Total candles: {total_candles}, time difference: {time_diff}, granularity in ms: {granularity_ms}")

        if total_candles == 0:
            return []

        calls = []
        current_start_time = start_time

        while total_candles > 0:
            candles_in_this_call = min(total_candles, max_candles_per_call)
            current_end_time = current_start_time + (candles_in_this_call * granularity_ms)

            calls.append({
                "start_time": current_start_time,
                "end_time": current_end_time,
                "candles": candles_in_this_call
            })

            current_start_time = current_end_time + granularity_ms
            total_candles -= candles_in_this_call

        print(f"Calculated API calls: {calls}")
        return calls

    def convert_granularity_to_ms(self, granularity: str) -> int:
        if granularity == "1m":
            return 60 * 1000
        elif granularity == "5m":
            return 5 * 60 * 1000
        elif granularity == "15m":
            return 15 * 60 * 1000
        elif granularity == "30m":
            return 30 * 60 * 1000
        elif granularity == "1H":
            return 3600 * 1000
        elif granularity == "4H":
            return 4 * 3600 * 1000
        elif granularity == "12H":
            return 12 * 3600 * 1000
        elif granularity == "1D":
            return 24 * 3600 * 1000
        elif granularity == "1W":
            return 7 * 24 * 3600 * 1000
        elif granularity == "1MO":
            return 30 * 24 * 3600 * 1000
        else:
            raise ValueError(f"Unsupported granularity: {granularity}")   

    async def get_candlestick_chart(self, symbol: str, granularity: str, start_time: int = None, end_time: int = None) -> np.ndarray:
            final_result = np.empty((0, 7))
            base_url = 'https://api.bitget.com/api/v2/mix/market/candles'
            params = {
                'symbol': symbol,
                'granularity': granularity,
                'productType': 'USDT-FUTURES',
                'limit': 1000
            }

            # Get how many times do I need to call the API
            granularity_ms = self.convert_granularity_to_ms(granularity)
            api_calls = self.calculate_api_calls(start_time, end_time, granularity_ms)
            # total_candles = (end_time - start_time) // granularity_ms
       
            
            async with aiohttp.ClientSession() as session:
                for i, call in enumerate(api_calls):
                    if start_time:
                        params['startTime'] = str(call['start_time'])
                    if end_time:
                        params['endTime'] = str(call['end_time'])

                    async with session.get(base_url, params=params) as response:
                        if response.status == 200:
                            result = await response.json()
                            data = result.get("data", [])

                            if not data:
                                print(f"there wasn't data in attempt {i}")
                                break

                            np_data = np.array([
                                [
                                    int(item[0]),    # The timestamp in milliseconds
                                    float(item[1]),  # Open price
                                    float(item[2]),  # High price
                                    float(item[3]),  # Low price
                                    float(item[4]),  # Close price
                                    float(item[5]),  # Volume (traded amount in the base currency)
                                    float(item[6])   # Notional value (the total traded value in quote currency)
                                ]
                                for item in data
                            ], dtype=object)

                            final_result = np.vstack([final_result, np_data])

                            last_timestamp = int(data[-1][0])

                            # If the last fetched timestamp reaches or exceeds the requested end_time, stop fetching data
                            if end_time and last_timestamp >= end_time:
                                break

                            # Update startTime to last_timestamp + 1 to continue fetching the next 1000 candles
                            params['startTime'] = str(last_timestamp + 1)

                        else:
                            print(f"Error fetching candlestick data: {response.status}")
                            break

            return final_result

    async def get_1min_candlestick_chart(self, symbol: str, startTime: int, endTime: int) -> np.ndarray:
        url = "https://api.bitget.com/api/v2/spot/market/candles"
        granularity = '1min'

        # Ensure startTime and endTime are in milliseconds and passed as strings
        params = {
            "symbol": symbol, 
            "granularity": granularity, 
            "startTime": str(startTime), 
            "endTime": str(endTime)  
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    data = result.get("data", [])

                    if not data:
                        print("No data returned from the API.")
                        return np.array([])

                    # Convert the data to a NumPy array with timezone conversion
                    utc = pytz.utc
                    amsterdam_tz = pytz.timezone('Europe/Amsterdam')

                    np_data = np.array([
                        [
                            datetime.fromtimestamp(int(item[0]) / 1000, tz=utc).astimezone(amsterdam_tz).timestamp(),  # Convert to Amsterdam timezone
                            float(item[1]),  # open price
                            float(item[2]),  # high price
                            float(item[3]),  # low price
                            float(item[4]),  # close price
                            float(item[5])   # volume in base currency
                        ]
                        for item in data if isinstance(item, list) and len(item) >= 6  # Ensure valid format
                    ])
                    return np_data
                else:
                    print(f"Error fetching candlestick data: {response.status}")
                    print(f"Api response: {await response.text()}")
                    return np.array([])


    
    async def get_market_cap(self, symbol: str):
        """Retrieve the market capitalization for a given cryptocurrency symbol using CoinMarketCap API."""
        base_url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {
            "X-CMC_PRO_API_KEY": COINMARKETCAP_APIKEY,
            "Accept": "application/json"
        }

        if symbol.lower().endswith('usdt'):
            symbol = symbol[:-4]
        
        params = {
            "symbol": symbol,
            "convert": "USD"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    try:
                        market_cap = data['data'][symbol]['quote']['USD']['market_cap']
                        return market_cap
                    except KeyError:
                        print(f"Market cap not found for symbol: {symbol}")
                        return None
                else:
                    print(f"Error fetching market cap data: {response.status}")
                    return None


    async def get_historical_funding_rate(self, symbol: str):
        url = "https://api.bitget.com/api/v2/mix/market/history-fund-rate"
        params = {"symbol": symbol, "productType": "USDT-FUTURES"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        data = result.get("data", [])

                        # Define a unique dtype for the structured array
                        dtype = [
                            ('fundingRateTimes100', 'float32'),  
                            ('fundingTimeEurope', 'U25'),
                            ('fundingTimeDefault', 'float32')  
                        ]
                        
                        # Convert the fetched data to a NumPy structured array
                        np_data = np.array([
                            (
                                float(fr["fundingRate"]) * 100,  # Funding rate times 100
                                datetime.utcfromtimestamp(int(fr["fundingTime"]) / 1000)  # Funding time as ISO string format
                                .replace(tzinfo=timezone('UTC'))
                                .astimezone(timezone('Europe/Amsterdam'))
                                .isoformat(),
                                float(fr["fundingTime"]),  # Funding time in default format
                            )
                            for fr in data
                        ], dtype=dtype)
                        
                        # Convert NumPy array to list of Python native types for serialization
                        return jsonable_encoder(np_data.tolist())
                    else:
                        print(f"Error fetching funding rate data: {response.status}")
                        return []
        except Exception as e:
            print(f"An error occurred: {e}")
            return []


    @property
    def api_timezone(self):
        return self._api_timezone


async def main_testing():
    bitget_layer = BitgetClient() 
    start_time = int(datetime(2024, 10, 6, 10).timestamp() * 1000)  
    end_time = int(datetime.now(pytz.utc).timestamp() * 1000)  
   
    granularity = '1m'  

    mk = await bitget_layer.get_market_cap('BTCUSDT')
    print("marketcap ->", mk)

    """
    res = await bitget_layer.get_candlestick_chart('BTCUSDT', granularity, start_time, end_time)
    print(res)
    print("length -> ", len(res))

    df = pd.DataFrame(res, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'notional'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.to_csv('delete_this.csv', index=False)
    """

    

if __name__ == "__main__":
    asyncio.run(main_testing())