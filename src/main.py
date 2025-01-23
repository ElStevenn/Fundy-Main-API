# main.py
# Author: Pau Mateu
# Developer email: paumat17@gmail.com
# v: 1.3.5

# Standard Library Imports
from contextlib import asynccontextmanager
from datetime import timedelta

# Third-Party Imports
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pytz import timezone

# Local Imports
from src.app.founding_rate_service.main_sercice_layer import FoundinRateService
from src.app.founding_rate_service.schedule_layer import ScheduleLayer
from src.app.founding_rate_service.bitget_layer import BitgetClient
from src.routes.user import user_router as user
from src.routes.auth import oauth_router as oauth
from src.routes.administrative import administrative_router as administrative
from src.routes.accounts import accounts_router as accounts
from src.routes.trading_bots import trading_bots_router as trading_bots
from src.config import DOMAIN

# Initialize Scheduler and Services
async_scheduler = ScheduleLayer("Europe/Amsterdam")
founding_rate_service = FoundinRateService()
bitget_client = BitgetClient()
background_task = None

# Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler
    async_scheduler.scheduler.start()
    print("Scheduler started.")

    # Initialize and start the Founding Rate Service
    if founding_rate_service.status != 'running':
        try:
            # Calculate next execution time
            next_execution_time = founding_rate_service.get_next_execution_time() - timedelta(minutes=5)
            founding_rate_service.next_execution_time = next_execution_time
            print(f"Scheduling 'innit_procces' at {next_execution_time.isoformat()} in timezone {founding_rate_service.timezone}")

            # Schedule the `innit_procces` method
            async_scheduler.schedule_process_time(next_execution_time, founding_rate_service.innit_procces)

            # Update the service status
            founding_rate_service.status = 'running'

            print("Founding Rate Service has been started successfully.")

        except Exception as e:
            print(f"Error starting Founding Rate Service: {e}")
            # Optionally, handle the exception (e.g., retry, alert, etc.)

    try:
        yield
    finally:
        # Shutdown the scheduler
        async_scheduler.scheduler.shutdown()
        print("Scheduler shut down.")

# Initialize FastAPI App
app = FastAPI(
    title="Fundy-Main-API",
    description=(
        "The **Fundy Main API** is a backend solution for managing trading accounts, user profiles, and cryptocurrency data.\n"
        "It ensures secure and efficient handling of sensitive data while offering tools for scheduling and automation.\n"
        "Designed for reliability and scalability, this API serves as the backbone for the **FUNDY** application.\n\n"

        "## **Core Capabilities**\n\n"

        "### **User Management**\n"
        "- Authentication via Google OAuth 2.0.\n"
        "- Manage user profiles and preferences.\n"
        "- Retrieve and update user-specific configurations.\n\n"

        "### **Account Management**\n"
        "- Configure trading and sub-accounts.\n"
        "- Set and retrieve the main trading account for each user.\n"
        "- Manage account permissions and associations.\n\n"

        "### **Cryptocurrency Features**\n"
        "- Retrieve cryptocurrencies with high funding rates.\n"
        "- Access historical funding rates for specific cryptocurrencies.\n"
        "- Save, highlight, and manage starred cryptocurrencies.\n\n"

        "### **Alerts and Scheduling**\n"
        "- Schedule periodic tasks and trading operations.\n"
        "- (Upcoming) Set price alerts for specific cryptocurrencies.\n\n"

        "### **Security**\n"
        "- RSA encryption for secure data handling.\n"
        "- Access the public key for encrypting sensitive information.\n\n"

        "### **Administrative Tools**\n"
        "- Monitor the status of internal services.\n"
        "- View recently joined users and system metrics.\n\n"
    ),
    lifespan=lifespan,
    version="1.3.4",
    contact={"name": "Pau Mateu", "url": "https://paumateu.com/", "email": "paumat17@gmail.com"},
    servers=[
        {"url": "http://pauservices.top/", "description": "Spain"},
        {"url": "http://localhost:8000/", "description": "localhost"},
    ],
)

# Ser routers
router = APIRouter()
app.include_router(oauth)
app.include_router(user)
app.include_router(accounts)
app.include_router(administrative)
app.include_router(trading_bots)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fundy.pauservices.top"] if DOMAIN else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Run Uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
