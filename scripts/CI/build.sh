#!/bin/bash

set -e

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

git -C /home/ubuntu/Fundy-Main-API pull origin main
sudo mkdir -p "$NGINX_CONF_DIR" "$NGINX_ENABLED_DIR"
mkdir -p "$SECURITY_PATH"

if [ ! -f "$PRIVATE_KEY" ]; then
    mkdir -p "$SECURITY_PATH"
    openssl genpkey -algorithm RSA -out "$PRIVATE_KEY" -pkeyopt rsa_keygen_bits:4096
    openssl rsa -pubout -in "$PRIVATE_KEY" -out "$PUBLIC_KEY"
fi

docker container stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker container rm "$CONTAINER_NAME" >/dev/null 2>&1 || true

if [ -f "$CONFIG" ]; then
    jq '.api = false' "$CONFIG" | sudo tee "$CONFIG" > /dev/null
fi

sudo ufw allow 'Nginx Full' || true
cd "$APP_DIR"
docker build -t "$IMAGE_NAME" .
docker run -d --name "$CONTAINER_NAME" --network "$NETWORK_NAME" -p 127.0.0.1:8000:8000 "$IMAGE_NAME"

sudo bash -c "cat > $NGINX_CONF" <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf "$NGINX_CONF" "$NGINX_ENABLED_DIR/fundy_api"
sudo rm -f /etc/nginx/sites-enabled/default || true
sudo nginx -t
sudo systemctl restart nginx

if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    sudo certbot certonly --webroot -w /var/www/html -d "$DOMAIN" -d "www.$DOMAIN" --non-interactive --agree-tos -m "$EMAIL"
fi

sudo bash -c "cat > $NGINX_CONF" <<EOF
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
EOF

sudo nginx -t
sudo systemctl reload nginx

if [ -f "$CONFIG" ]; then
    if [[ -s "$CONFIG" ]]; then
        API=\$(jq -r '.api' "$CONFIG")
        if [[ "\$API" == "false" ]]; then
            sudo jq '.api = true' "$CONFIG" | sudo tee "$CONFIG" > /dev/null
        fi
    fi
fi

bash /home/ubuntu/scripts/CI/unit_testing.sh
