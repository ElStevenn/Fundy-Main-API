#!/bin/bash

set -e

# Adjust these variables
DOMAIN="pauservices.top"
EMAIL="paumat17@gmail.com" 
APP_DIR="/home/ubuntu/Fundy-Main-API"
CONFIG="/home/ubuntu/scripts/config.json"

SECURITY_PATH="$APP_DIR/src/security"
PRIVATE_KEY="$SECURITY_PATH/private_key.pem"
PUBLIC_KEY="$SECURITY_PATH/public_key.pem"
IMAGE_NAME="fundy_main_api"
CONTAINER_NAME="fundy_main_api_v1"
NETWORK_NAME="my_network"
NGINX_CONF_DIR="/etc/nginx/sites-available"
NGINX_ENABLED_DIR="/etc/nginx/sites-enabled"
NGINX_CONF="$NGINX_CONF_DIR/fundy_api"

# Ensure directories
sudo mkdir -p $NGINX_CONF_DIR $NGINX_ENABLED_DIR
if [ ! -d "$SECURITY_PATH" ]; then
    mkdir -p "$SECURITY_PATH"
fi

# Generate keys if needed
if [ ! -f "$PRIVATE_KEY" ]; then
    echo "Generating private key..."
    openssl genpkey -algorithm RSA -out "$PRIVATE_KEY" -pkeyopt rsa_keygen_bits:4096
    echo "Generating public key..."
    openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"
fi

# Ensure .env file
[ ! -f "$APP_DIR/src/.env" ] && touch "$APP_DIR/src/.env"

# Stop and remove existing container
docker container stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker container rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
if [ -f "$CONFIG" ]; then
    jq '.api = false' "$CONFIG" > temp.json && mv temp.json "$CONFIG"
fi

# Update packages and install Nginx, Certbot
sudo apt-get update -y
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Allow Nginx through firewall if UFW is enabled
sudo ufw allow 'Nginx Full' || true

# Build Docker image
cd "$APP_DIR" || exit 1
docker build -t "$IMAGE_NAME" .

# Run the container mapped to localhost:8000
docker run -d --name "$CONTAINER_NAME" --network "$NETWORK_NAME" -p 127.0.0.1:8000:8000 "$IMAGE_NAME"

# Create basic HTTP config
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

sudo ln -sf "$NGINX_CONF" "$NGINX_ENABLED_DIR/fundy_api"
sudo rm -f /etc/nginx/sites-enabled/default || true

# Test Nginx configuration and restart
sudo nginx -t
sudo systemctl restart nginx

# Obtain SSL certificate
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m $EMAIL
fi

# If Certbot didn't update config, do it manually
if ! grep -q "listen 443 ssl" "$NGINX_CONF"; then
    echo "Manually configuring SSL..."
    sudo bash -c "cat > $NGINX_CONF" <<EOL
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;º
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL
    sudo nginx -t
    sudo systemctl reload nginx
fi

# Update the API flag
if [ -f "$CONFIG" ]; then
    if [[ -s "$CONFIG" ]]; then
        API=$(jq -r '.api' "$CONFIG")
        if [[ "$API" == "false" ]]; then
            jq '.api = true' "$CONFIG" > temp.json && mv temp.json "$CONFIG"
        fi
    fi
fi

echo "Setup complete. Your application should now be accessible via https://$DOMAIN/"
