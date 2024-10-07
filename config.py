import os
from dotenv import load_dotenv

load_dotenv()

# Bitget
BITGET_APIKEY = os.getenv('BITGET_APIKEY')
BITGET_SECRET_KEY = os.getenv('BITGET_SECRET_KEY')
BITGET_PASSPHRASE = os.getenv('BITGET_PASSPHRASE')


# Constants & Configuration
MIN_FOUNDING_RATE = -0.5 # os.getenv('MIN_FOUNDING_RATE', -1.5)
MAX_FOUNDING_RATE = 1.5 # os.getenv('MAX_FOUNDING_RATE', 1.5)
LEVERAGE = os.getenv('LEVERAGE', 5)
AMOUNT_ORDER = 10 # At this version, the amount of money per order is fixed 

# Database
DB_NAME = os.getenv('DB_NAME', 'db-name')
DB_USER = os.getenv('DB_USER', 'username')
DB_PASS = os.getenv('DB_PASS', 'password')
DB_HOST = os.getenv('DB_HOST', '0.0.0.0')

# Google Oauth
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', 'your-google-client-id')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', 'your-client-sercret')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost/google/callback')

# Security 
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key-here')
FRONTEND_IP = os.getenv('FRONTEND_IP', 'https//0.0.0.0/')
HISTORICAL_FR_API_IP = os.getenv('HISTORICAL_FR_API_IP', 'https//0.0.0.0/')

# API-KEYS
COINMARKETCAP_APIKEY = os.getenv('COINMARKETCAP_APIKEY', 'coinmarketcap-apikey')