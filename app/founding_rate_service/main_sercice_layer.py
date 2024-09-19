import asyncio
from datetime import datetime, time, timedelta
from typing import Literal, Optional
import pytz

from app.founding_rate_service.bitget_layer import BitgetClient
from app.redis_service import RedisService
from app.founding_rate_service.chart_analysis import FundingRateChart
from config import (
    MIN_FOUNDING_RATE,
    MAX_FOUNDING_RATE,
    AMOUNT_ORDER
)


class FoundinRateService:
    def __init__(self) -> None:
        self.first_execution_times = [
            time(hour, minute)
            for hour in range(24)
            for minute in range(0, 60, 15)
        ]
        self.timezone = "Europe/Amsterdam"
        self.next_execution_time: Optional[datetime] = None

        # Other configurations
        self.max_trades = 1  # Change to 3 as needed
        self.status = 'stopped'

        self.cryptos = []

        # Initialize clients
        self.bitget_client = BitgetClient()
        self.redis_service = RedisService()

    def get_next_execution_time(self, ans: bool = False) -> datetime:
        now_datetime = datetime.now(pytz.timezone(self.timezone))
        now_time = now_datetime.time()

        sorted_times = sorted(t for t in self.first_execution_times if t > now_time)
        if sorted_times:
            next_time_of_day = sorted_times[1] if ans and len(sorted_times) > 1 else sorted_times[0]
        else:
            next_time_of_day = self.first_execution_times[0]

        next_execution_datetime = datetime.combine(
            now_datetime.date(),
            next_time_of_day,
            tzinfo=pytz.timezone(self.timezone)
        )

        if next_execution_datetime <= now_datetime:
            next_execution_datetime += timedelta(days=1)

        return next_execution_datetime

    async def innit_procces(self):
        try:
            print("Initiating the process! This function should be executed 5 minutes before the funding rate")
            future_cryptos = await self.bitget_client.get_future_cryptos()
            sorted_future_cryptos = self.bitget_client.fetch_future_cryptos(future_cryptos)

            negative_funding_rate = [
                {"symbol": d["symbol"], "mode": "long", "fundingRate": float(d["fundingRate"])}
                for d in sorted_future_cryptos
                if float(d["fundingRate"]) <= float(MIN_FOUNDING_RATE)
            ]
            for crypto in negative_funding_rate:
                self.cryptos.append({"symbol": crypto["symbol"], "fundingRate": crypto["fundingRate"]})

            positive_funding_rate = [
                {"symbol": d["symbol"], "mode": "short", "fundingRate": float(d["fundingRate"])}
                for d in sorted_future_cryptos
                if float(d["fundingRate"]) >= float(MAX_FOUNDING_RATE)
            ]
            for crypto in positive_funding_rate:
                self.cryptos.append({"symbol": crypto["symbol"], "fundingRate": crypto["fundingRate"]})

            end_process = bool(negative_funding_rate or positive_funding_rate)
            if end_process:
                print("There were cryptos to trade!!! Reprogramming in 5 min!")
                for crypto in negative_funding_rate:
                    if crypto['fundingRate'] < 1.3:
                        asyncio.create_task(self.schedule_open_long(crypto, 'normal'))

                    if crypto['fundingRate'] >= 3.0:
                        limit = 60  # Define an appropriate limit value
                        chart = FundingRateChart(crypto['symbol'], granularity='1min', limit=limit)
                        last_funding_rates = chart.determine_by_past_funding_rates()
                        if last_funding_rates['result'] == 'long':
                            asyncio.create_task(self.schedule_open_long(crypto, last_funding_rates['type'])

                            )
                        elif last_funding_rates['result'] == 'short':
                            asyncio.create_task(self.schedule_open_short(crypto, last_funding_rates['type']))
                        else:
                            asyncio.create_task(self.schedule_open_short(crypto, 'after'))

                    if crypto['fundingRate'] < 3.0:
                        limit = (60 * 8) * 2  # 2 periods at this moment
                        chart = FundingRateChart(crypto['symbol'], granularity='1min', limit=limit)
                        await chart.fetch_data()
                        await chart.fetch_funding_rate_expiration_time()

                        # Open trades that involve analysis to the chart
                        percentage, _ = chart.analyze_last_volatility()
                        if percentage >= 1.5:  # If the last volatility was higher than 1.5, open short as 'after'
                            asyncio.create_task(self.schedule_open_short(crypto, 'after'))
                        else:
                            incrementation_analysis = await chart.analyze_incrementation()

                            if incrementation_analysis['result']:
                                if incrementation_analysis['side'] == 'short':
                                    asyncio.create_task(self.schedule_open_short(crypto, incrementation_analysis['type']))
                                elif incrementation_analysis['side'] == 'long':
                                    asyncio.create_task(self.schedule_open_long(crypto, incrementation_analysis['type']))

            else:
                print("There weren't cryptos to trade! Reprogramming for the next wave")

            print("Programming next wave even though there are already cryptos..")
            if self.status == 'running':
                self.schedule_next_execution()

        except Exception as e:
            print(f"Error in innit_procces: {e}")

    def schedule_next_execution(self):
        next_execution_time = self.get_next_execution_time(ans=True) - timedelta(minutes=5)
        print(f"Scheduled 'innit_procces' at {next_execution_time.strftime('%Y-%m-%d %H:%M:%S')} in timezone {self.timezone}")

        delay = (next_execution_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()
        if delay < 0:
            delay = 0  # Execute immediately if the time has already passed

        self.next_execution_time = next_execution_time
        asyncio.create_task(self._schedule_after_delay(delay, self.innit_procces))

    async def _schedule_after_delay(self, delay: float, coro):
        try:
            await asyncio.sleep(delay)
            await coro()
        except Exception as e:
            print(f"Error in scheduled task: {e}")

    async def open_order(self, symbol: str, mode: str):
        try:
            print(f"Opening order: Symbol={symbol}, Mode={mode}")
            await self.bitget_client.open_order(
                symbol=symbol,
                amount=AMOUNT_ORDER,
                mode=mode
            )
        except Exception as e:
            print(f"Error opening order for {symbol} in {mode} mode: {e}")

    async def close_order(self, symbol: str):
        try:
            print(f"Closing order: Symbol={symbol}")
            await self.bitget_client.close_order(symbol)

            save_operation_time = datetime.now(pytz.timezone(self.timezone)) + timedelta(seconds=30)
            delay = (save_operation_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()
            delay = max(delay, 0)  # Ensure non-negative delay

            asyncio.create_task(self._schedule_after_delay(delay, lambda: self.save_operation(symbol)))
        except Exception as e:
            print(f"Error closing order for {symbol}: {e}")

    async def schedule_open_long(self, crypto: dict, type: Literal['normal', 'after', 'after-variation'] = 'normal', close_delay: Optional[int] = 5) -> None:
        symbol = crypto['symbol']
        print(f"Scheduling a long for {symbol}, type: {type}")

        stmx = self.get_next_execution_time()
        if type == 'normal':
            """Open a long 45 secs before and close 15 secs after the funding rate"""
            open_long_time = stmx - timedelta(seconds=45)
            delay_open = (open_long_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()

            close_time = stmx + timedelta(seconds=15)
            delay_close = (close_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()

        elif type == 'after':
            """Open a long 15 secs after the funding rate and close after a delay"""
            open_long_time = stmx + timedelta(seconds=15)
            delay_open = (open_long_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()

            close_time = open_long_time + timedelta(minutes=close_delay)
            delay_close = (close_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()

        elif type == 'after-variation':
            """Open long after funding rate and close after 5 hours"""
            open_long_time = stmx + timedelta(minutes=2)
            delay_open = (open_long_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()

            close_time = open_long_time + timedelta(hours=5)
            delay_close = (close_time - datetime.now(pytz.timezone(self.timezone))).total_seconds()

        else:
            print(f"Unknown type {type} for scheduling open long.")
            return

        delay_open = max(delay_open, 0)
        delay_close = max(delay_close, 0)

        print(f"Scheduled to open long for {symbol} at {open_long_time.strftime('%Y-%m-%d %H:%M:%S')}")
        asyncio.create_task(self._schedule_after_delay(delay_open, lambda: self.open_order(symbol, 'long')))

        print(f"Scheduled to close long for {symbol} at {close_time.strftime('%Y-%m-%d %H:%M:%S')}")
        asyncio.create_task(self._schedule_after_delay(delay_close, lambda: self.close_order(symbol)))

    async def schedule_open_short(self, crypto: dict, type: Literal['normal', 'after', 'after-variation'] = 'normal') -> None:
        symbol = crypto['symbol']
        print(f"Scheduling a short for {symbol}, type: {type}")

        stmx = self.get_next_execution_time()
        if type == 'normal':
            """Open a short 45 secs before and close 15 secs after the funding rate"""
            operation_open = stmx - timedelta(seconds=45)
            operation_close = stmx + timedelta(seconds=15)

        elif type == 'after':
            """Open a short 15 secs after the funding rate and close after 60 secs"""
            operation_open = stmx + timedelta(seconds=15)
            operation_close = operation_open + timedelta(seconds=60)

        elif type == 'after-variation':
            """Open short after funding rate and close after 10 minutes"""
            operation_open = stmx + timedelta(seconds=15)
            operation_close = operation_open + timedelta(minutes=10)

        else:
            print(f"Unknown type {type} for scheduling open short.")
            return

        delay_open = (operation_open - datetime.now(pytz.timezone(self.timezone))).total_seconds()
        delay_close = (operation_close - datetime.now(pytz.timezone(self.timezone))).total_seconds()

        delay_open = max(delay_open, 0)
        delay_close = max(delay_close, 0)

        print(f"Scheduled to open short for {symbol} at {operation_open.strftime('%Y-%m-%d %H:%M:%S')}")
        asyncio.create_task(self._schedule_after_delay(delay_open, lambda: self.open_order(symbol, 'short')))

        print(f"Scheduled to close short for {symbol} at {operation_close.strftime('%Y-%m-%d %H:%M:%S')}")
        asyncio.create_task(self._schedule_after_delay(delay_close, lambda: self.close_order(symbol)))

    async def save_operation(self, symbol: str):
        try:
            print(f"Saving operation for {symbol}")
            # Get Historical Pnl of the last operation | https://www.bitget.com/api-doc/contract/position/Get-History-Position
            position_pnl_data = await self.bitget_client.get_pnl_order(symbol)

            # Save data
            self.redis_service.add_new_pnl(position_pnl_data)
            print(f"Operation data saved for {symbol}")
        except Exception as e:
            print(f"Error saving operation for {symbol}: {e}")

    async def start_service(self):
        if self.status == 'running':
            print("Service is already running.")
            return

        self.status = 'running'
        print("Starting FoundinRateService...")
        self.schedule_next_execution()

    def stop_service(self):
        if self.status == 'stopped':
            print("Service is already stopped.")
            return

        self.status = 'stopped'
        print("Stopping FoundinRateService...")
        # Implement any necessary cleanup here

    ### TESTING - DELETE THIS IF NOT NEEDED ####
    def test_schedule(self):
        order_time = datetime.now(pytz.timezone(self.timezone)) + timedelta(seconds=30)
        print(f"Testing schedule at {order_time.strftime('%Y-%m-%d %H:%M:%S')}")
        asyncio.create_task(self._schedule_after_delay(30, self.random_function))

    async def random_function(self):
        print("RANDOM FUNCTION!")
        order_lol = await self.bitget_client.get_pnl_order("BTCUSDT")
        print(order_lol)


async def main():
    service = FoundinRateService()
    await service.start_service()

    # Keep the service running indefinitely
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, adjust as needed
    except (KeyboardInterrupt, SystemExit):
        await service.stop_service()


if __name__ == "__main__":
    asyncio.run(main())
