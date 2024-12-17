#!/bin/bash

# Paths
PRIVATE_KEY="/home/ubuntu/Fundy-Main-API/src/security/private_key.pem"
PUBLIC_KEY="/home/ubuntu/Fundy-Main-API/src/security/public_key.pem"


# Creaste public and private key
if [ ! -f "$PRIVATE_KEY" ]; then
    echo "Private key not found. Generating private key..."
    openssl genpkey -algorithm RSA -out "$PRIVATE_KEY" -pkeyopt rsa_keygen_bits:4096

    echo "Extracting public key from the private key..."
    openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"
else
    echo "Private key already exists. Skipping key generation."
fi
# Create .env file
if [ ! -f "/home/ubuntu/Fundy-Main-API/src/.env" ]; then
    touch /home/ubuntu/Fundy-Main-API/src/.env
fi


# Variables
image_name="fundy_main_api"
container_nme="fundy_main_api_v1"
network_name="my_network"

# Stop and remove the application container
docker container stop "$container_nme"
docker container rm "$container_nme"

# Build image
cd /home/ubuntu/Fundy-Main-API
docker build -t "$image_name" .

# Run the application container on the custom network and expose port 80
docker run -d -p 8080:80 --name "$container_nme" --network "$network_name" "$image_name"



