from config import BITGET_APIKEY, BITGET_PASSPHRASE, BITGET_SECRET_KEY, LEVERAGE
from fastapi import HTTPException
from typing import Optional, Literal
import pandas as pd
import asyncio
import aiohttp
import hmac
import base64
import json
import time



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
        mac = hmac.new(bytes(self.api_secret_key, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
        return base64.b64encode(mac.digest()).decode()

    def get_headers(self, method: str, request_path: str, query_string: str, body: str) -> dict:
        timestamp = self.get_timestamp()
        
        # Construct the prehash string according to the presence of query_string
        if query_string:
            prehash_string = f"{timestamp}{method.upper()}{request_path}?{query_string}{body}"
        else:
            prehash_string = f"{timestamp}{method.upper()}{request_path}{body}"

        sign = self.generate_signature(prehash_string)

        return {
            "Content-Type": "application/json",
            "ACCESS-KEY": self.apikey,
            "ACCESS-SIGN": sign,
            "ACCESS-PASSPHRASE": self.passphrase,
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
        url = f"http://3.141.197.183:8000/close_order/{symbol}"
        headers = {
            "password": "mierda69",
            "Content-Type": "application/json"  
        }
        data = {
            "price": 0
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data) as response:
                content_type = response.headers.get('Content-Type')
                if content_type and 'application/json' in content_type:
                    data = await response.json()
                else:
                    data = await response.text()
                    if data == 'Internal Server Error':
                        raise HTTPException(status_code=400, detail= f"Internal server errror while closing the opration: {data}")
                return data




async def main_testing():
    # Open order test 
    bitget_client = BitgetClient()
    api_response = await bitget_client.open_order(symbol="AVAIL", mode="short", amount=10)
    print(api_response)


async def close_order_test():
    bitget_client = BitgetClient()
    api_response = bitget_client.close_order("URDI")
    print(api_response)

if __name__ == "__main__":
    asyncio.run(main_testing())