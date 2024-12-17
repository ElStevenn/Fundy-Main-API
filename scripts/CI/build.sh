#!/bin/bash

# Paths
config="/home/ubuntu/scripts/config.json"
SECURITY_PATH="/home/ubuntu/Fundy-Main-API/src/security"
PRIVATE_KEY="$SECURITY_PATH/private_key.pem"
PUBLIC_KEY="$SECURITY_PATH/public_key.pem"

DOMAIN="pauservices.top"
EMAIL="your-email@example.com"  # Replace with a valid email
NGINX_CONF="/etc/nginx/sites-available/fundy_api"
NGINX_ENABLED="/etc/nginx/sites-enabled/fundy_api"

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

# Install Nginx and Certbot
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Allow Nginx full profile if using UFW firewall
sudo ufw allow 'Nginx Full' || true

# Build the Docker image
cd /home/ubuntu/Fundy-Main-API || exit 1
docker build -t "$image_name" .

# Run the application container (internal mapping to localhost:8000)
docker run -d --name "$container_nme" --network "$network_name" -p 127.0.0.1:8000:8000 "$image_name"

# Create a basic HTTP config first
if [ ! -f "$NGINX_CONF" ]; then
    echo "Creating Nginx configuration for HTTP..."
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
    sudo ln -sf $NGINX_CONF $NGINX_ENABLED
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# Test and restart Nginx
sudo nginx -t && sudo systemctl restart nginx

# Obtain SSL certificates and configure Nginx for HTTPS using Certbot
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    echo "Generating SSL certificate for $DOMAIN and www.$DOMAIN..."
    # Certbot should automatically edit the config to use SSL
    sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m $EMAIL
else
    echo "SSL certificate already exists. Skipping Certbot."
fi

# After Certbot run, ensure we have an SSL config
if ! grep -q "listen 443 ssl" "$NGINX_CONF"; then
    echo "Certbot did not configure SSL automatically. Manually configuring SSL..."
    # Manually configure the Nginx SSL server block
    sudo bash -c "cat > $NGINX_CONF" <<EOL
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    # Redirect all HTTP to HTTPS
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
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOL
    sudo nginx -t && sudo systemctl reload nginx
fi

# Update the API flag in config if it exists
if [ -f "$config" ]; then
    if [[ -s "$config" ]]; then
        API=$(jq -r '.api' "$config")
        if [[ "$API" == "false" ]]; then
            jq '.api = true' "$config" > temp.json && mv temp.json "$config"
        fi
    fi
fi

echo "Setup complete. Your application should now be accessible via https://$DOMAIN/"
