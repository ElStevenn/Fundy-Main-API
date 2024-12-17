#!/bin/bash

redis_container="redis_tasks"
network_name="my_network"
redis_port=6378
image_name="main_api"
container_name="localhost_main_api_v1"

# Stop and remove the application container
docker container stop $container_name >/dev/null 2>&1
docker container rm $container_name >/dev/null 2>&1

# Remove the old application image
docker image rm $image_name >/dev/null 2>&1

echo "Build and Run container? (y/n)"
read response

if [ "$response" == "y" ]; then
    # Build and run the application container
    docker build -t $image_name .

    # Run the application container on the custom network and expose port 8000
    docker run -d -p 8000:8000 --name $container_name --network $network_name $image_name

    echo "Application container '$container_name' is up and running."

    echo "Do you want to see the logs? (y/n)"
    read response
    if [ "$response" == "y" ]; then
        docker logs --follow $container_name
    fi

else
    echo "Deployment aborted."
fi
