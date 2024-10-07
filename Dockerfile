# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /

# Install pip packages directly
RUN pip install --no-cache-dir fastapi aiohttp uvicorn pydantic requests schedule bs4 lxml pytz httpx python-dotenv redis pandas apscheduler sqlalchemy alembic pyjwt asyncpg scipy

# Copy the rest of the application code into the container
COPY . .

# Expose the ports that the application uses
EXPOSE 80 8080

# Set the command to run the application
RUN ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]