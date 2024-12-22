#!/bin/bash
set -e

# Variables
DOMAIN="pauservices.top"
EMAIL="paumat17@gmail.com"
APP_DIR="/home/ubuntu/Fundy-Main-API"
CONFIG="/home/ubuntu/scripts/config.json"
IMAGE_NAME="fundy_main_api"
CONTAINER_NAME="fundy_main_api_v1"
NETWORK_NAME="my_network"
NGINX_CONF_DIR="/etc/nginx/sites-available"
NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"
NGINX_CONF="$NGINX_CONF_DIR/fundy_api"

# Read configuration
FIRST_TIME=$(jq -r '.first_time' "$CONFIG")

# Ensure Nginx configuration directories exist
sudo mkdir -p "$NGINX_CONF_DIR" "$NGINX_ENABLED_DIR"

# Update the application if not the first time
if [[ "$FIRST_TIME" == "false" ]]; then
    git -C "$APP_DIR" pull origin main
fi

# Stop and remove existing Docker container
docker container stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker container rm "$CONTAINER_NAME" >/dev/null 2>&1 || true

# Update configuration file if it exists
if [ -f "$CONFIG" ]; then
    jq '.api = false' "$CONFIG" | sudo tee "$CONFIG" > /dev/null
fi

# Allow Nginx through the firewall
sudo ufw allow 'Nginx Full' || true

# Build and run the Docker container with correct port mapping
cd "$APP_DIR"
docker build -t "$IMAGE_NAME" .
docker run -d --name "$CONTAINER_NAME" --network "$NETWORK_NAME" -p 127.0.0.1:8000:8000 "$IMAGE_NAME"

# Create Nginx server block for HTTP (temporary for Certbot)
sudo bash -c "cat > $NGINX_CONF" <<EOL
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

# Enable the Nginx configuration
sudo ln -sf "$NGINX_CONF" "$NGINX_ENABLED_DIR/fundy_api"
sudo rm -f /etc/nginx/sites-enabled/default || true

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx

# Obtain SSL certificate if not already present
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m $EMAIL
fi

# Update Nginx configuration to use HTTPS
sudo bash -c "cat > $NGINX_CONF" <<EOL
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$host\$request_uri;
}

# HTTPS Server Block
server {
    listen 443 ssl;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL

# Test and reload Nginx with the new configuration
sudo nginx -t
sudo systemctl reload nginx

# Update configuration file to indicate API is active
if [ -f "$CONFIG" ]; then
    if [[ -s "$CONFIG" ]]; then
        API=$(jq -r '.api' "$CONFIG")
        if [[ "$API" == "false" ]]; then
            sudo jq '.api = true' "$CONFIG" | sudo tee "$CONFIG" > /dev/null
        fi
    fi
fi

# Update 'first_time' flag if necessary
if [[ "$FIRST_TIME" == "true" ]]; then
    jq '.first_time = false' "$CONFIG" > temp.json && mv temp.json "$CONFIG"
fi

# Run unit tests or additional scripts
bash /home/ubuntu/scripts/CI/unit_testing.sh
