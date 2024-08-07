import aiohttp, asyncio, json, os
from bs4 import BeautifulSoup
from typing import Literal
from dotenv import load_dotenv
import requests

load_dotenv()


class Asset_Alert():
 
    def __init__(self) -> None:
        pass

    async def get_asset_price(self, asset_name, type_asset: Literal["indices", "crypto", ""]):
        if type_asset == "indices":
            result = await self.get_indices(asset_name)
        elif type_asset == "crypto":
            result = await self.get_crypto()
        
        return result
    
    async def get_crypto(self, crypto_name: str):
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': os.getenv('apikey'),
        }
        parameters = {
            'slug': crypto_name.lower()
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=parameters) as response:
                result = await response.json()
                if ['status']['error_code'] != 0:
                    return result
                else:
                    raise ValueError(f"An error ocurred: {['status']['error_message']}")


    async def get_indices(self, asset_name):
        url = f"https://www.investing.com/indices/{asset_name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.text()
                soup = BeautifulSoup(content, "lxml")
                div_min = soup.find('div', class_='min-w-0')
                price_div = div_min.find('div', class_='text-5xl/9 font-bold text-[#232526] md:text-[42px] md:leading-[60px]')
                
                return price_div.text if price_div else None




async def main_test():
    asset_alert = Asset_Alert()
    res = await asset_alert.get_crypto("bitcoin")

    print(res)


if __name__ == "__main__":
    asyncio.run(main_test())
