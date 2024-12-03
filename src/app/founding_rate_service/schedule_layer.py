# schedule_layer.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from datetime import time as dt_time, datetime, timedelta
from typing import Callable, Coroutine

class ScheduleLayer:
    def __init__(self, timezone: str):
        self.timezone = timezone
        self.first_execution_times = [dt_time(hour, minute) for hour in range(24) for minute in range(0, 60, 15)]
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(self.timezone))
        # Removed: self.scheduler.start()

    def schedule_process_time(self, run_time: datetime, function_to_call: Callable[..., Coroutine], *args):
        timezone = pytz.timezone(self.timezone)
        if run_time.tzinfo is None:
            run_time = timezone.localize(run_time)
        else:
            run_time = run_time.astimezone(timezone)

        self.scheduler.add_job(
            self._run_async_function, 
            'date', 
            run_date=run_time, 
            args=[function_to_call, *args], 
            coalesce=True, 
            misfire_grace_time=30
        )
        print(f"Scheduled '{function_to_call.__name__}' at {run_time} in timezone {self.timezone}")

    async def _run_async_function(self, function_to_call: Callable[..., Coroutine], *args):
        print(f"Executing function '{function_to_call.__name__}' with args: {args}")
        await function_to_call(*args)

    def get_next_execution_time(self, ans: bool = False) -> datetime:
        timezone = pytz.timezone(self.timezone)
        now_datetime = datetime.now(timezone)
        now_time = now_datetime.time()
        sorted_times = sorted(t for t in self.first_execution_times if t > now_time)
        if sorted_times:
            next_time_of_day = sorted_times[1] if ans and len(sorted_times) > 1 else sorted_times[0]
        else:
            next_time_of_day = self.first_execution_times[0]
        
        # Combine current date with next_time_of_day
        naive_datetime = datetime.combine(now_datetime.date(), next_time_of_day)
        
        # Localize the naive datetime to the specified timezone
        next_execution_datetime = timezone.localize(naive_datetime)
        
        # If the scheduled time is in the past, schedule for the next day
        if next_execution_datetime <= now_datetime:
            next_execution_datetime += timedelta(days=1)
        
        return next_execution_datetime

    def stop_all_jobs(self):
        """Stops all scheduled jobs."""
        self.scheduler.remove_all_jobs()
        print("All scheduled jobs have been removed.")