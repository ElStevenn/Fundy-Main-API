from datetime import datetime, time, timedelta
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

    def get_next_execution_time(self) -> datetime:
        now_datetime = datetime.now(pytz.timezone(self.timezone))
        now_time = now_datetime.time()

        next_time_of_day = min(
            (t for t in self.first_execition_times if t > now_time),
            default=self.first_execition_times[0]
        )

        next_execution_datetime = datetime.combine(now_datetime.date(), next_time_of_day, tzinfo=pytz.timezone(self.timezone))

        # If the next execution time is earlier than now, schedule it for the next day
        if next_execution_datetime <= now_datetime:
            next_execution_datetime += timedelta(days=1)

        return next_execution_datetime

    def schedule_initial_execution(self):
        # Schedule `innit_procces` 5 minutes before the next scheduled time
        next_execution_time = self.get_next_execution_time() - timedelta(minutes=5)
        print(f"Scheduled 'innit_procces' at {next_execution_time.strftime('%H:%M')} in timezone {self.timezone}")
        self.scheduler.schecule_process_time(next_execution_time, lambda: asyncio.run(self.innit_procces()))

    async def innit_procces(self):
        """Main process to trigger the rest of the components of this program."""
        # GET CRYPTOS WITH HIGH INTEREST RATE
        future_cryptos = await bitget_client.get_future_cryptos()
        sorted_future_cryptos = bitget_client.fetch_future_cryptos(future_cryptos)
        print(sorted_future_cryptos)

        # Cryptos to consider for opening a long position
        open_long_cryptos = [{"symbol": d["symbol"], "mode": "long", "fundingRate": float(d["fundingRate"])} 
                             for d in sorted_future_cryptos if float(d["fundingRate"]) <= float(MIN_FOUNDING_RATE)]
        for crypto in open_long_cryptos:
            redis_service.add_new_crypto_lead(crypto["symbol"], crypto["fundingRate"])

        # Cryptos to consider for opening a short position
        open_short_cryptos = [{"symbol": d["symbol"], "mode": "short", "fundingRate": float(d["fundingRate"])} 
                              for d in sorted_future_cryptos if float(d["fundingRate"]) >= float(MAX_FOUNDING_RATE)]
        for crypto in open_short_cryptos:
            redis_service.add_new_crypto_lead(crypto["symbol"], crypto["fundingRate"])

        # Determine if the process should continue based on available cryptos
        end_process = bool(open_long_cryptos or open_short_cryptos)
        print(end_process)

        if end_process:
            print("Cryptos found for processing!")
            stmx = self.get_next_execution_time()

            # Schedule task to open the order (1 min before the execution)
            next_execution_time = stmx - timedelta(minutes=1)
            print("Next execution time to open the order->", next_execution_time)
            self.scheduler.schecule_process_time(next_execution_time, lambda: asyncio.run(self.open_orders(stmx)))

    async def open_orders(self, execution_time: datetime):
        # GET SAVED CRYPTOS ->
        print("The orders are being opened!")
        saved_cryptos = redis_service.read_all_crypto_lead()

        final_trade_data = []
        for crypto in saved_cryptos:
            symbol = crypto['symbol'].removesuffix("USDT")
            data = {
                "symbol": symbol,
                "mode": crypto['mode'],
                "amount": AMOUNT_ORDER
            }
            final_trade_data.append(data)

        await asyncio.gather(*[bitget_client.open_order(**data) for data in final_trade_data])

        next_execution_time = execution_time + timedelta(seconds=15)
        self.scheduler.schecule_process_time(next_execution_time, lambda: asyncio.run(self.close_orders()))

    async def close_orders(self):
        print("The order are beeing closing..")
        # Get SAVED CRYPTOS ->
        saved_cryptos = redis_service.read_all_crypto_lead()

        final_trade_data = []
        for crypto in saved_cryptos:
            symbol = crypto['symbol'].removesuffix("USDT")
            data = {
                "symbol": symbol,
                "mode": crypto['mode'],
                "amount": AMOUNT_ORDER
            }
            final_trade_data.append(data)
        await asyncio.gather(*[bitget_client.close_order(symbol=data['symbol']) for data in final_trade_data])

    def start_service(self):
        # Schedule the initial process 5 minutes before the next scheduled time
        self.schedule_initial_execution()
        self.scheduler.start_background()


async def main_testing():
    founding_rate_service = FoundinRateService()
    founding_rate_service.start_service()

if __name__ == "__main__":
    asyncio.run(main_testing())
