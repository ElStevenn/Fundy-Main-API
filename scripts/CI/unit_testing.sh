#!/bin/bash

container_name="fundy_main_api_v1"

# Set up tables if needed
docker cp /home/ubuntu/Fundy-Main-API/src/app/database/database.py $container_name:/app/database.py
docker exec -it $container_name python /app/database.py


