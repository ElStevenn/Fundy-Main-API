# !/bin/bash

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

    # Run container in needed port 
    docker run -d -p 80:80 --name scheduler_v1 scheduler

    # Get relevant data
    ip=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' scheduler_v1)
    host_port=$(docker inspect --format='{{(index (index .NetworkSettings.Ports "8000/tcp") 0).HostPort}}' scheduler_v1)
    host=$(curl ifconfig.me)

    echo "----------------------------------------------------"
    echo "Container Name: scheduler_v1"
    echo "Container running on http://${host}:$port" 

else
    # Check if redis container exists
    
    docker run -it --network some-network --rm redis redis-cli -h some-redis

    echo "Ok."
fi