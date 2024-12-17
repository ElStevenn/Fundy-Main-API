#!/bin/bash

# Paths
config="/home/ubuntu/scripts/config.json"
SECURITY_PATH="/home/ubuntu/Fundy-Main-API/src/security"
PRIVATE_KEY="$SECURITY_PATH/private_key.pem"
PUBLIC_KEY="$SECURITY_PATH/public_key.pem"

# Ensure security directory exists
if [ ! -d "$SECURITY_PATH" ]; then
    mkdir -p "$SECURITY_PATH"
fi

# Create public and private keys if they do not exist
if [ ! -f "$PRIVATE_KEY" ]; then
    echo "Private key not found. Generating private key..."
    openssl genpkey -algorithm RSA -out "$PRIVATE_KEY" -pkeyopt rsa_keygen_bits:4096
    echo "Extracting public key from the private key..."
    openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"
else
    echo "Private key already exists. Skipping key generation."
fi

# Create .env file if it doesn't exist
if [ ! -f "/home/ubuntu/Fundy-Main-API/src/.env" ]; then
    touch "/home/ubuntu/Fundy-Main-API/src/.env"
fi

# Variables
image_name="fundy_main_api"
container_nme="fundy_main_api_v1"
network_name="my_network"

# Stop and remove the application container if it exists
docker container stop "$container_nme" >/dev/null 2>&1
docker container rm "$container_nme" >/dev/null 2>&1
if [ -f "$config" ]; then
    jq '.api = false' "$config" > temp.json && mv temp.json "$config"
fi

# Update and install Nginx and Certbot
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Ensure firewall allows HTTPS (optional, depending on your firewall config)
sudo ufw allow 'Nginx Full' || true

# Build the Docker image
cd /home/ubuntu/Fundy-Main-API || exit 1
docker build -t "$image_name" .

# Run the application container internally on 8000
docker run -d --name "$container_nme" --network "$network_name" -p 127.0.0.1:8000:8000 "$image_name"

NGINX_CONF="/etc/nginx/sites-available/fundy_api"
if [ ! -f "$NGINX_CONF" ]; then
    echo "Creating Nginx configuration for HTTP..."
    sudo bash -c "cat > $NGINX_CONF" <<EOL
server {
    listen 80;
    server_name pauservices.top www.pauservices.top;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL
    sudo ln -s /etc/nginx/sites-available/fundy_api /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# Test and restart Nginx
sudo nginx -t && sudo systemctl restart nginx

# Obtain SSL certificates and let Certbot configure Nginx for HTTPS
if [ ! -d "/etc/letsencrypt/live/pauservices.top" ]; then
    echo "Generating SSL certificate for pauservices.top and www.pauservices.top..."
    sudo certbot --nginx -d pauservices.top -d www.pauservices.top --non-interactive --agree-tos -m your-email@example.com
else
    echo "SSL certificate already exists. Skipping Certbot."
fi

# Reload Nginx with SSL configuration
sudo systemctl reload nginx

# Update the API flag in config if it exists
if [ -f "$config" ]; then
    if [[ -s "$config" ]]; then
        API=$(jq -r '.api' "$config")
        if [[ "$API" == "false" ]]; then
            jq '.api = true' "$config" > temp.json && mv temp.json "$config"
        fi
    fi
fi

echo "Setup complete. Your application should now be accessible via https://pauservices.top/"
