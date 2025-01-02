#!/bin/bash
set -e

# Adjust these variables as needed
APP_DIR="/home/ubuntu/Fundy-Main-API"
CONFIG="/home/ubuntu/scripts/config.json"
IMAGE_NAME="fundy_main_api"
CONTAINER_NAME="fundy_main_api_v1"
NETWORK_NAME="my_network"
DOMAIN="pauservices.top"

# Stop and remove the existing container if it exists
docker container stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker container rm "$CONTAINER_NAME" >/dev/null 2>&1 || true

# (Optional) Rebuild the Docker image if code changed
cd "$APP_DIR" || exit 1w
docker build -t "$IMAGE_NAME" .

# Run the container mapped to localhost:8000
docker run -d --name "$CONTAINER_NAME" --network "$NETWORK_NAME" -p 127.0.0.1:8000:8000 "$IMAGE_NAME"

# Reload Nginx to ensure it detects the new container instance
sudo nginx -t
sudo systemctl reload nginx

# Update the API flag in config to true
if [ -f "$CONFIG" ]; then
    if [[ -s "$CONFIG" ]]; then
        API=$(jq -r '.api' "$CONFIG")
        if [[ "$API" == "false" ]]; then
            jq '.api = true' "$CONFIG" > temp.json && mv temp.json "$CONFIG"
        fi
    fi
fi

echo "Server restart complete. Your application should now be running behind Nginx at https://$DOMAIN/"
