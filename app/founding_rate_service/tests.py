import os
import asyncio
import schedule
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

from app.redis_service import RedisService
from app.founding_rate_service.schedule_layer import ScheduleLayer
from app.founding_rate_service.bitget_layer import BitgetClient

"""
    Test to see if everything works properly and adjusted with my thoughts
"""

schedulere_service = ScheduleLayer("Europe/Amsterdam")
bitget_client = BitgetClient()
real_scheduler = AsyncIOScheduler(timezone=timezone('Europe/Amsterdam'))

def next_execution_time_test(minutes = 5) -> datetime:
    today = datetime.now(timezone('Europe/Amsterdam'))
    next_time = today + timedelta(minutes=minutes)
    return next_time



async def test1():
    """Test to see if the scheduler works as I want"""
    first_execution_time = next_execution_time_test(3)
    second_execution_time = next_execution_time_test(5)


    real_scheduler.add_job(func=bitget_client.open_order, args=["ORDI", 10, "short"], trigger='date', run_date=first_execution_time)
    real_scheduler.add_job(func=bitget_client.close_order, args=["ORDI"], trigger='date', run_date=second_execution_time)

    print(f"Scheduled execution time: {first_execution_time} & open order")
    print(f"Scheduled execituon time: {second_execution_time} & close order")

    # Start the scheduler and keep it running
    real_scheduler.start()

    # Keep the program running until all scheduled jobs are executed
    await asyncio.Event().wait()  # This will keep the event loop running indefinitely




if __name__ == "__main__":
    asyncio.run(test1())
