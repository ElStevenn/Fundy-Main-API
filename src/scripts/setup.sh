#!/bin/bash

echo "Is this the first time that you're executing this? (y/n)"
read response
if [ "$response" != "y" ]; then
    exit
fi

# Define variables for network and volume names
network_name="my_network"
volume_name="data_volume"
redis_container="redis_tasks"

# Create network if it doesn't exist
docker network inspect $network_name > /dev/null 2>&1
if [ $? -ne 0 ]; then
    docker network create $network_name
    echo "Network '$network_name' created."
fi

# Create volume if it doesn't exist
docker volume inspect $volume_name > /dev/null 2>&1
if [ $? -ne 0 ]; then
    docker volume create $volume_name
    echo "Volume '$volume_name' created."
fi

# Check if Redis container exists
red_container=$(docker container ls | grep $redis_container)

# If the container doesn't exist, start it with the network and volume
if [ -z "$red_container" ]; then
    docker run -d --name $redis_container --network $network_name -p 6379:6379 -v $volume_name:/data redis 
    echo "Redis container '$redis_container' started."
else
    echo "Redis container '$redis_container' is already running."
fi
