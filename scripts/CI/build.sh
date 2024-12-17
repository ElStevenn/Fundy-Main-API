#!/bin/bash

# Paths
config="/home/ubuntu/scripts/config.json"
SECURITY_PATH="/home/ubuntu/Fundy-Main-API/src/security"
PRIVATE_KEY="$SECURITY_PATH/private_key.pem"
PUBLIC_KEY="$SECURITY_PATH/public_key.pem"

if [ ! -d "$SECURITY_PATH" ]; then
    mkdir -p "$SECURITY_PATH"
fi

# Create public and private keys
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
    touch "/home/ubuntu/Fundy-Main-API/src/.env"
fi

# Variables
image_name="fundy_main_api"
container_nme="fundy_main_api_v1"
network_name="my_network"

# Stop and remove the application container
docker container stop "$container_nme" >/dev/null 2>&1
docker container rm "$container_nme" >/dev/null 2>&1
jq '.api = false' "$config" > temp.json && mv temp.json "$config"


# Build image
cd /home/ubuntu/Fundy-Main-API || exit
docker build -t "$image_name" .

# Run the application container on the custom network and expose port 80
docker run -d -p 80:8000 --name "$container_nme" --network "$network_name" "$image_name"


if [ -f "$config" ]; then
    if [[ -s "$config" ]]; then
        API=$(jq -r '.api' "$config")
        if [[ "$API" == "false" ]]; then
            jq '.api = true' "$config" > temp.json && mv temp.json "$config"
        fi
    fi
fi