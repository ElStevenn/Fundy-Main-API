#!/bin/bash

config="/home/ubuntu/scripts/config.json"

# Variables
network_name="my_network"
volumes_name="my_volumes"
postgres_image="my_postgres"
postgres="my_postgres_v1"


# Configure
if [ -f "$config" ]; then
    echo "Config file found"

    # Check if the file has content
    if [[ -s "$config" ]]; then

        NETWORK=$(jq -r '.network' "$config")
        VOLUMES=$(jq -r '.volumes' "$config")
        POSTGRES=$(jq -r '.postgres' "$config")
        FIRST_TIME=$(jq -r '.first_time' "$config")

        if [[ "$NETWORK" == "false" ]]; then
            # Set up network
            echo "Setting up network"
            docker network create --driver bridge "$network_name"

            jq '.network = true' "$config" > temp.json && mv temp.json "$config"
        fi

        if [[ "$VOLUMES" == "false" ]]; then
            # Set up volumes
            echo "Setting up volumes"
            docker volume create --name "$volumes_name"

            jq '.volumes = true' "$config" > temp.json && mv temp.json "$config"
        fi

        if [[ "$POSTGRES" == "false" ]]; then
            # Set up postgres
            echo "Setting up postgres"
            docker pull postgres:13.2
            docker run -d \
                --name "$postgres" \
                --network "$network_name" \
                -e POSTGRES_PASSWORD=test_password \
                -e POSTGRES_USER=test_user \
                -e POSTGRES_DB=main_db \
                -v "$volumes_name":/var/lib/postgresql/data \
                postgres:13.2

            jq '.postgres = true' "$config" > temp.json && mv temp.json "$config"
        fi

        if [[ "$FIRST_TIME" == "true" ]]; then
            # Set up first time
            echo "Running first-time setup..."
            git clone https://github.com/ElStevenn/Fundy-Main-API.git
            cd Fundy-Main-API

            jq '.first_time = false' "$config" > temp.json && mv temp.json "$config"

        else
            git pull origin main
            cd Fundy-Main-API
        fi

        # Call Static code analysis -> Build Testing Application -> Run Tests | 

    else
        echo "Config file is empty"
    fi

else
    echo "Config file not found"
fi
