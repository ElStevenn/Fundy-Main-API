#!/bin/bash

config="/home/ubuntu/scripts/config.json"

# Variables
network_name="my_network"
volumes_name="my_volumes"
postgres_image="my_postgres"
postgres="my_postgres_v1"

# Update packages and install dependencies
sudo apt-get update -y

# Install required packages
sudo apt-get install -y nginx certbot python3-certbot-nginx jq git docker.io


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

            sudo jq '.network = true' "$config" | sudo tee "$config" > /dev/null
        fi

        if [[ "$VOLUMES" == "false" ]]; then
            # Set up volumes
            echo "Setting up volumes"
            docker volume create --name "$volumes_name"

            sudo jq '.volumes = true' "$config" | sudo tee "$config" > /dev/null
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
            -p 5432:5432 \
            postgres:13.2

            sudo jq '.postgres = true' "$config" | sudo tee "$config" > /dev/null
        fi

        if [[ "$FIRST_TIME" == "true" ]]; then
            # Set up first time
            echo "Running first-time setup..."
            git clone https://github.com/ElStevenn/Fundy-Main-API.git
            mkdir -p /home/ubuntu/Fundy-Main-API/src/security
            
            git config --global --add safe.directory /home/ubuntu/Fundy-Main-API

        else
            cd /home/ubuntu/Fundy-Main-API
            git config --global --add safe.directory /home/ubuntu/Fundy-Main-API
            sleep 2

        fi

        # Call Static code analysis -> Build Testing Application -> Run Tests | 

    else
        echo "Config file is empty"
        exit 1
    fi

else
    echo "Config file not found"
    exit 1
fi
