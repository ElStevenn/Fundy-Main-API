#!/bin/bash

redis_container="redis_tasks"
network_name="my_network"

# Stop and remove container
docker container stop scheduler_v1
docker container rm scheduler_v1

# Remove Image
docker image rm scheduler

echo "Build and Run container? (y/n)"
read response

if [ "$response" == "y" ]; then
    # Build container
    docker build -t scheduler .

    # Run container on the custom network
    docker run -d -p 80:80 --name scheduler_v1 --network $network_name scheduler

    # Get relevant data
    ip=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' scheduler_v1)
    host_port=$(docker inspect --format='{{(index (index .NetworkSettings.Ports "80/tcp") 0).HostPort}}' scheduler_v1)
    host=$(curl -s ifconfig.me)

    echo "----------------------------------------------------"
    echo "Container Name: scheduler_v1"
    echo "Container running on http://${host}:${host_port}" 

else
    # Check if Redis container exists
    red_container=$(docker container ls | grep $redis_container)

    # If the container doesn't exist, start it with the volume
    if [ -z "$red_container" ]; then
        docker run -d --name redis_tasks -v data_volume:/data -p 6378:6379 redis:latest
        echo "Redis container '$redis_container' started."
    else
        echo "Redis container '$redis_container' is already running."
    fi

    echo "Ok."
fi
