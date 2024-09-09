from config import BITGET_APIKEY, BITGET_PASSPHRASE, BITGET_SECRET_KEY, LEVERAGE
from fastapi import HTTPException
from typing import Optional, Literal
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
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
                
    async def get_candlestick_chart(self, symbol: str, granularity: Granularity = '1min', limit: int = 100) -> np.ndarray:
        url = 'https://api.bitget.com/api/v2/spot/market/candles'
        params = {'symbol': symbol, 'granularity': granularity, 'limit': limit}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        data = result.get("data", [])
                        
                        if not data:
                            print("No data returned from the API.")
                            return np.array([])

                        # Convert the data to a NumPy array with timezone conversion using pytz
                        utc = pytz.utc
                        amsterdam_tz = pytz.timezone('Europe/Amsterdam')
                        
                        np_data = np.array([
                            [
                                utc.localize(datetime.utcfromtimestamp(int(item[0]) / 1000)).astimezone(amsterdam_tz).timestamp(),  # Convert to Amsterdam timezone
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
                        print("error response -> ",response)
                        return np.array([])
        except Exception as e:
            print(f"An error occurred: {e}")
            return np.array([])


    async def get_historical_funding_rate(self, symbol: str):
        url = "https://api.bitget.com/api/v2/mix/market/history-fund-rate"
        params = {"symbol": symbol, "productType": "USDT-FUTURES"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        data = result.get("data", [])
                        return data
                    else:
                        print(f"Error fetching funding rate data: {response.status}")
                        return []
        except Exception as e:
            print(f"An error occurred: {e}")
            return []


async def main_testing():
    # Open order test 
    bitget_client = BitgetClient()
    api_response = await bitget_client.get_historical_funding_rate("SLFUSDT")

    print(api_response)

if __name__ == "__main__":
    asyncio.run(main_testing())