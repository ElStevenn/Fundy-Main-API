from datetime import datetime, time, timedelta
from typing import Literal
import pytz
import asyncio
import threading

from app.founding_rate_service.bitget_layer import BitgetClient
# from app.founding_rate_service.schedule_layer import ScheduleLayer
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
        self.next_execution_time = None

        # Other configuration
        self.max_trades = 1  # I'll change this to 3 soon
        self.status = 'stopped'


    def get_next_execution_time(self, ans = False) -> datetime:
        now_datetime = datetime.now(pytz.timezone(self.timezone))
        now_time = now_datetime.time()

        next_time_of_day = (
            sorted((t for t in self.first_execition_times if t > now_time))
            [1 if ans else 0]
            if len(self.first_execition_times) > 1 and any(t > now_time for t in self.first_execition_times)
            else self.first_execition_times[0]
        )

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
        next_execution_time = self.get_next_execution_time() - timedelta(minutes=5)
        print(f"Scheduled 'innit_procces' at {next_execution_time.strftime('%H:%M')} in timezone {self.timezone}")

        delay = (next_execution_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()
        loop = asyncio.get_event_loop()
        loop.call_later(delay, lambda: asyncio.run_coroutine_threadsafe(self.innit_procces(), loop))
        
        self.next_execution_time = next_execution_time


    async def innit_procces(self):
        """Main process to trigger the rest of the components of this program."""
        # GET CRYPTOS WITH HIGH INTEREST RATE
        print("Innitating the innit proces! This function should be executed 5 minutes before the founing rate")
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
            print("There wasn't cryptos to trade! Reprogramming for the next wave")
            if self.status == 'running':
                next_execution_time = self.get_next_execution_time(True) - timedelta(minutes=5)
                print(f"Scheduled 'innit_procces' at {next_execution_time.strftime('%H:%M')} in timezone {self.timezone}")

                # Calculate delay in seconds until the target datetime
                delay = (next_execution_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()

                # Re-schedule the asynchronous function to run once
                loop = asyncio.get_event_loop()
                loop.call_later(delay, lambda: asyncio.run_coroutine_threadsafe(self.innit_procces(), loop))
                
                self.next_execution_time = next_execution_time  



  

    async def open_order(self, symbol, mode):
        print("The orders are being opened!")

        await bitget_client.open_order(
            symbol=symbol,
            amount=AMOUNT_ORDER,
            mode=mode
        )

    async def close_order(self, symbol):
        print("The order are being closed.")
        await bitget_client.close_order(symbol)

        # Schedule `save_operation` 30 seconds after the order is closed
        save_operation_time = datetime.now(pytz.timezone(self.timezone)) + timedelta(seconds=30)
        
        delay = (save_operation_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()

        loop = asyncio.get_event_loop()
        loop.call_later(delay, lambda: asyncio.run_coroutine_threadsafe(self.save_operation(symbol), loop))

        

        
    async def schedule_open_long(self, symbol, type) -> None:
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
        self.next_execution_time = next_execution_time

    async def schedule_open_short(self, symbol, type: Literal['normal', 'after', 'after-variation'] = 'normal') -> None:
        next_execution_time = self.get_next_execution_time()
        print(f"Opening a short for {symbol}")

        if type == 'normal':
            operation_open = next_execution_time + timedelta(seconds=45)
            operation_close = next_execution_time + timedelta(seconds=15)
            self.scheduler.schedule_process_time(operation_open, self.open_order, args=[symbol, 'long'])
            self.scheduler.schedule_process_time(operation_close, self.close_order, args=[symbol]); self.next_execution_time = operation_close

        elif type == 'after':
            operation_open = next_execution_time
            operation_close = next_execution_time + timedelta(seconds=60)
            self.scheduler.schedule_process_time(operation_open, self.open_order, args=[symbol, 'long'])
            self.scheduler.schedule_process_time(operation_close, self.close_order, args=[symbol]); self.next_execution_time = operation_close

        elif type == 'after-variation':
            operation_open = next_execution_time + timedelta(seconds=15)
            operation_close = next_execution_time + timedelta(minutes=10)
            self.scheduler.schedule_process_time(operation_open, self.open_order, args=[symbol, 'long'])
            self.scheduler.schedule_process_time(operation_close, self.close_order, args=[symbol]); self.next_execution_time = operation_close


    async def save_operation(self, symbol):
        # Get Historical Pnl of the last operation | https://www.bitget.com/api-doc/contract/position/Get-History-Position
        position_pnl_data = await bitget_client.get_pnl_order(symbol)

        # Save data
        redis_service.add_new_pnl(position_pnl_data)
    

    async def start_service(self):
        self.schedule_initial_execution()
        self.status = 'running'
        
        # Start the scheduler in the background
        asyncio.create_task(self.scheduler.start_background())




    def stop_service(self):
        self.scheduler.stop_background()
        self.status = 'stopped'


    ### TESTING - DELETE THIS SHIT #### 
    def test_schedule(self):
        order_time = datetime.now() + timedelta(seconds=30)
        self.scheduler.schedule_process_time(order_time, self.random_function)


    async def random_function(self):
        print("RANDOM FUNCTION!")
        order_lol = await bitget_client.get_pnl_order("BTCUSDT")
        print(order_lol)


async def main_testing():
    founding_rate_service = FoundinRateService()
    future_cryptos = await bitget_client.get_future_cryptos()
    sorted_future_cryptos = bitget_client.fetch_future_cryptos(future_cryptos)


    print(sorted_future_cryptos)
    print("ans prefouning rate -> ", founding_rate_service.get_next_execution_time(True))

if __name__ == "__main__":
    asyncio.run(main_testing())
