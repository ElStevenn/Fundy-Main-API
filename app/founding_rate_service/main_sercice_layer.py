from datetime import datetime, time, timedelta
from typing import Literal
import pytz
import asyncio

from app.founding_rate_service.bitget_layer import BitgetClient
from app.founding_rate_service.schedule_layer import ScheduleLayer
from app.redis_service import RedisService
from config import ( 
    MIN_FOUNDING_RATE, 
    MAX_FOUNDING_RATE,
    AMOUNT_ORDER
)

bitget_client = BitgetClient()
redis_service = RedisService()


class FoundinRateService():
    def __init__(self) -> None:
        self.first_execition_times = [time(2, 0), time(10, 0), time(18, 0)]
        self.timezone = "Europe/Amsterdam"
        self.scheduler = ScheduleLayer(self.timezone)

        # Other configuration
        self.max_trades = 1  # I'll change this to 3 soon
        self.status = 'stopped'


    def get_next_execution_time(self, ans = False) -> datetime:
        now_datetime = datetime.now(pytz.timezone(self.timezone))
        now_time = now_datetime.time()

        next_time_of_day = sorted(
            (t for t in self.first_execition_times if t > now_time)
        )[1 if ans else 0] if len(self.first_execition_times) > 1 else self.first_execition_times[0]

        next_execution_datetime = datetime.combine(now_datetime.date(), next_time_of_day, tzinfo=pytz.timezone(self.timezone))

        # If the next execution time is earlier than now, schedule it for the next day
        if next_execution_datetime <= now_datetime:
            next_execution_datetime += timedelta(days=1)

        return next_execution_datetime

    def get_datetime_execution_time(seconds: int) -> datetime:
        """Get executuion time adding seconds"""
        now_datetime = datetime.now()
        next_execution_time = now_datetime + timedelta(seconds=seconds)
        return next_execution_time

    def schedule_initial_execution(self):
        # Schedule `innit_procces` 5 minutes before the next scheduled time
        next_execution_time = self.get_next_execution_time() - timedelta(minutes=5)
        print(f"Scheduled 'innit_procces' at {next_execution_time.strftime('%H:%M')} in timezone {self.timezone}")
        self.scheduler.schedule_process_time(next_execution_time, self.innit_procces)

    async def innit_procces(self):
        """Main process to trigger the rest of the components of this program."""
        # GET CRYPTOS WITH HIGH INTEREST RATE
        future_cryptos = await bitget_client.get_future_cryptos()
        sorted_future_cryptos = bitget_client.fetch_future_cryptos(future_cryptos)


        # Cryptos to consider for opening a long position
        negative_founding_rate = [{"symbol": d["symbol"], "mode": "long", "fundingRate": float(d["fundingRate"])} 
                             for d in sorted_future_cryptos if float(d["fundingRate"]) <= float(MIN_FOUNDING_RATE)]
        for crypto in negative_founding_rate:
            redis_service.add_new_crypto_lead(crypto["symbol"], crypto["fundingRate"])

        # Cryptos to consider for opening a short position
        positive_founding_rate = [{"symbol": d["symbol"], "mode": "short", "fundingRate": float(d["fundingRate"])} 
                              for d in sorted_future_cryptos if float(d["fundingRate"]) >= float(MAX_FOUNDING_RATE)]
        for crypto in positive_founding_rate:
            redis_service.add_new_crypto_lead(crypto["symbol"], crypto["fundingRate"])


 
        # Determine if the process should continue based on available cryptos
        end_process = bool(negative_founding_rate or positive_founding_rate)
        if end_process:
            # DETERMINE SHORT - LONG | HERE IS WHERE THE CONDITION ARE
            for crypto in negative_founding_rate:
            
                if crypto['fundingRate'] < 1.3:
                    # OPEN LONG, at this moment if founing rate is less than 1.3 always open long
                    asyncio.create_task(self.schedule_open_long(crypto))
        else:
            print("There wasn't cryptos to trade! Re programming for the next wave")
            


        
  

    async def open_order(self, symbol, mode):
        print("The orders are being opened!")

        await bitget_client.open_order(
            symbol=symbol,
            amount=AMOUNT_ORDER,
            mode=mode
        )

    async def close_order(self, symbol):
        print("The order are beeing clossed.")
        await bitget_client.close_order(symbol)

        # self.scheduler.schedule_process_time(next_execution_time, self.close_order, args=[symbol])

        # Scheck status and continue
        if self.status == 'running':
            # Schedule next process
            next_execution_time = self.get_next_execution_time() - timedelta(minutes=5)
            print(f"Scheduled 'innit_procces' at {next_execution_time.strftime('%H:%M')} in timezone {self.timezone}")
            self.scheduler.schedule_process_time(next_execution_time, next_execution_time)
        
    async def schedule_open_long(self, symbol) -> None:
        print(f"Scheduling a long in {symbol}")
        stmx = self.get_next_execution_time()

        # Schedule task to open the order (1 min before the execution)
        next_execution_time = stmx - timedelta(minutes=1)
        print("Next execution time to open the order->", next_execution_time)
        self.scheduler.schedule_process_time(next_execution_time, self.open_order, args=[symbol, 'long'])



        # Schedule task, close order 
        next_execution_time = stmx + timedelta(seconds=15)
        print(f"Close Order: {next_execution_time.strftime("%H:%M")}")
        self.scheduler.schedule_process_time(next_execution_time, self.close_order, args=[symbol])

    async def schedule_open_short(self, symbol, type=Literal['normal', 'after', 'after-variation']) -> None:
        
        if type == 'normal':
            pass

        elif type == 'after':
            pass

        elif type == 'after-variation':
            pass


    async def save_operation(self, symbol):

        # Get Historical Pnl of the last operation | https://www.bitget.com/api-doc/contract/position/Get-History-Position
        position_pnl_data = await bitget_client.get_pnl_order(symbol)

        # Save data
        redis_service.add_new_pnl(position_pnl_data)
    

    def start_service(self):
        # Schedule the initial process 5 minutes before the next scheduled time
        self.schedule_initial_execution()
        self.scheduler.start_background()
        self.status = 'running'

    def stop_service(self):
        self.scheduler.stop_background()
        self.status = 'stopped'




async def main_testing():
    founding_rate_service = FoundinRateService()
    future_cryptos = await bitget_client.get_future_cryptos()
    sorted_future_cryptos = bitget_client.fetch_future_cryptos(future_cryptos)


    print(sorted_future_cryptos)
    print("ans prefouning rate -> ", founding_rate_service.get_next_execution_time())

if __name__ == "__main__":
    asyncio.run(main_testing())
