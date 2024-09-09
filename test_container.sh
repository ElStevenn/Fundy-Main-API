#!/bin/bash

redis_container="redis_tasks"
network_name="my_network"
redis_port=6378

# Stop and remove the application container
docker container stop testing_scheduler
docker container rm testing_scheduler

# Remove the old image
docker image rm scheduler

# Prompt the user to input the module or path to test
echo "Type the module or script path you want to test in the format '-m module_name' or 'script_path':"
read path

echo "Build and Run container for testing? (y/n)"
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

    # Build the testing container
    docker build -t scheduler .

    # Run the testing container on the custom network
    docker run -d --name testing_scheduler --network $network_name scheduler

    # Execute the test inside the running container
    echo "Running the test command inside the container..."
    docker exec testing_scheduler python3 /app/$path

    # Ask the user if they want to see the logs
    echo "Wanna see the logs? (y/n)"
    read see_logs
    if [ "$see_logs" == "y" ]; then
        docker logs --follow testing_scheduler
    fi
else
    echo "Testing aborted."
fi
