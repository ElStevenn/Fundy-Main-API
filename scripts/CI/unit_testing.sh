#!/bin/bash

container_name="fundy_main_api_v1"

# Set up tables if needed
docker cp /home/ubuntu/Fundy-Main-API/src/app/database/database.py $container_name:/src/app/database/database.py
docker exec -it -w / fundy_main_api_v1 python -m src.app.database.database




