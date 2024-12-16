# Use the official Python image from the Docker Hub
FROM python:3

# Set the working directory in the container
WORKDIR /

# Install pip packages directly
RUN pip install --no-cache-dir -r requirements.txt
# Copy the rest of the application code into the container
COPY . .

# Expose the ports that the application uses
EXPOSE 80 8080

# Set the command to run the application
RUN ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]