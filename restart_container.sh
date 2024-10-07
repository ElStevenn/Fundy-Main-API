#!/bin/bash

redis_container="redis_tasks"
network_name="my_network"
redis_port=6378

# Stop and remove the application container
docker container stop scheduler_v1
docker container rm scheduler_v1

# Remove the old application image
docker image rm scheduler

echo "Build and Run container? (y/n)"
read response

if [ "$response" == "y" ]; then
    # Check if Redis network exists, create if not
    if ! docker network ls | grep -q "$network_name"; then
        docker network create "$network_name"
        echo "Network '$network_name' created."
    else
        echo "Network '$network_name' already exists."
    fi

    # Check if Redis container exists
    if ! docker container ls -a | grep -q "$redis_container"; then
        echo "Starting Redis container..."
        docker run -d --name $redis_container --network $network_name -v data_volume:/data -p $redis_port:6379 redis:latest
    else
        # If Redis container exists but is stopped, start it
        if [ "$(docker inspect -f '{{.State.Running}}' $redis_container)" == "false" ]; then
            docker start $redis_container
            echo "Redis container '$redis_container' started."
        else
            echo "Redis container '$redis_container' is already running."
        fi
    fi

    # Build the application container
    docker build -t scheduler .

    # Run the application container on the custom network and expose port 8000
    docker run -d -p 8000:8000 --name scheduler_v1 --network $network_name scheduler

    # Get relevant data
    ip=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' scheduler_v1)
    host_port=$(docker inspect --format='{{(index (index .NetworkSettings.Ports "8000/tcp") 0).HostPort}}' scheduler_v1)
    host=$(curl -s ifconfig.me)

    echo "----------------------------------------------------"
    echo "Container Name: scheduler_v1"
    echo "Container running on http://${host}:${host_port}" 

    # Ask user if he wants to see the logs
    echo "Wanna see the logs?(y/n)"
    read see_lgs
    if [ "$see_lgs" == "y" ]; then
        docker logs --follow scheduler_v1
    fi

else
    echo "Deployment aborted."
fi
