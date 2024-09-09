from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz
from datetime import datetime, timedelta
import asyncio
from typing import Callable, Coroutine

class ScheduleLayer:
    def __init__(self, timezone: str):
        self.timezone = timezone
        # Initialize the AsyncIO Scheduler
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone(self.timezone))
        self.scheduler.start()

    def schedule_process_time(self, time: datetime, function_to_call: Callable[[], Coroutine], *args):
        # Convert time to local time in the specified timezone
        local_time = time.astimezone(pytz.timezone(self.timezone))

        # Schedule the async function using AsyncIOScheduler
        self.scheduler.add_job(func=function_to_call, args=args, trigger='date', run_date=local_time)
        print(f"Scheduled '{function_to_call.__name__}' at {local_time} in timezone {self.timezone}")

    async def a_function(self, parameter):
        print(f"Hello! This is a function with the parameter: {parameter}")
        await asyncio.sleep(1.0)
        print(f"The function with the parameter {parameter} has finished!")

    def start_background(self):
        # Start the scheduler in a new event loop
        def run_loop():
            loop = asyncio.new_event_loop()  # Create a new event loop
            asyncio.set_event_loop(loop)  # Set the new event loop for the current thread
            try:
                loop.run_forever()  # Run the event loop forever
            except (KeyboardInterrupt, SystemExit):
                pass

        # Start the loop in a separate thread
        import threading
        threading.Thread(target=run_loop).start()

    def stop_background(self):
        # Stop the scheduler
        self.scheduler.shutdown(wait=False)
        print("Scheduler has been stopped.")

        # Stop the event loop
        loop = asyncio.get_event_loop()
        loop.stop()
        print("Event loop has been stopped.")




















# Example usage
if __name__ == "__main__":
    scheduler_service = ScheduleLayer("Europe/Amsterdam")

    # Define execution times
    def next_execution_time_test(minutes=5) -> datetime:
        today = datetime.now(pytz.timezone('Europe/Amsterdam'))
        next_time = today + timedelta(minutes=minutes)
        return next_time

    first_execution_time = next_execution_time_test(3)
    second_execution_time = next_execution_time_test(5)

    # Schedule the functions
    scheduler_service.schedule_process_time(first_execution_time, scheduler_service.a_function, "Pompeye!")
    scheduler_service.schedule_process_time(second_execution_time, scheduler_service.a_function, "Far-right parameter!")

    # Start the scheduler to keep running in the background
    scheduler_service.start_background()
