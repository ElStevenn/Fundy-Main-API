import schedule
import pytz
from datetime import datetime
import asyncio
from typing import Callable, Coroutine

class ScheduleLayer:
    def __init__(self, timezone):
        self.timezone = timezone

    def schecule_process_time(self, time: datetime, function_to_call: Callable[[], Coroutine]):
        local_time = time.astimezone(pytz.timezone(self.timezone))
        time_str = local_time.strftime("%H:%M")

        # Schedule the async function wrapped in a sync function
        schedule.every().day.at(time_str).do(self.run_async, function_to_call)
        print(f"Scheduled '{function_to_call.__name__}' at {time_str} in timezone {self.timezone}")

    def run_async(self, function_to_call: Callable[[], Coroutine]):
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(function_to_call())
        finally:
            loop.close()

    async def run_pending(self):
        while True:
            schedule.run_pending()
            await asyncio.sleep(1)

    def start_background(self):
        # Run the event loop for the scheduler in a new thread
        asyncio.run(self.run_pending())
