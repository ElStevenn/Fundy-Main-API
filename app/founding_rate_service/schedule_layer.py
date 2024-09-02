import schedule
import pytz
from datetime import datetime
import asyncio
from typing import Callable, Coroutine

class ScheduleLayer:
    def __init__(self, timezone):
        self.timezone = timezone

    def schecule_process_time(self, time, function_to_call: Callable[[], Coroutine]):
        local_time = time.astimezone(pytz.timezone(self.timezone))
        time_str = local_time.strftime("%H:%M")

        # Schedule the async function wrapped in a sync function
        schedule.every().day.at(time_str).do(self.run_async, function_to_call)
        print(f"Scheduled '{function_to_call.__name__}' at {time_str} in timezone {self.timezone}")

    def run_async(self, function_to_call: Callable[[], Coroutine]):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(function_to_call())
        else:
            loop.run_until_complete(function_to_call())

    async def run_pending(self):
        while True:
            schedule.run_pending()
            await asyncio.sleep(1)

    def start_background(self):
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(self.run_pending())
        else:
            loop.run_until_complete(self.run_pending())