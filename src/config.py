import os
import socket
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HOSTNAME = socket.gethostname()

# Bitget
BITGET_APIKEY = os.getenv('BITGET_APIKEY')
BITGET_SECRET_KEY = os.getenv('BITGET_SECRET_KEY')
BITGET_PASSPHRASE = os.getenv('BITGET_PASSPHRASE')


# Constants & Configuration
MIN_FOUNDING_RATE = -0.5 # os.getenv('MIN_FOUNDING_RATE', -1.5)
MAX_FOUNDING_RATE = 1.5 # os.getenv('MAX_FOUNDING_RATE', 1.5)
LEVERAGE = os.getenv('LEVERAGE', 5)
AMOUNT_ORDER = 10 # At this version, the amount of money per order is fixed 

# Local - Test Database enviroment
DB_NAME = os.getenv('DB_NAME', 'db-name')

if HOSTNAME == 'mamadocomputer':
    DB_HOST = os.getenv('LOCAL_DB_HOST', None)
    DB_USER = os.getenv('LOCAL_DB_USER', None)
    DB_PASS = os.getenv('LOCAL_DB_PASS', 'password')

    GOOGLE_REDIRECT_URI = 'http://localhost:8000/oauth/google/callback'
    FRONTEND_IP = os.getenv('LOCAL_FRONTEND_IP', None)
    DOMAIN = None

else:
    DB_HOST = os.getenv('TEST_DB_HOST', '0.0.0.0')
    DB_USER = os.getenv('TEST_DB_USER', None)
    DB_PASS = os.getenv('TEST_DB_PASS', 'password')

    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', None)
    FRONTEND_IP = os.getenv('TEST_FRONTEND_IP', None)
    DOMAIN = os.getenv('TEST_DOMAIN', None)


# Google Oauth
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', 'your-google-client-id')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', 'your-client-sercret')

# Telegram Oauth
TELEGRAM_ACCES_TOKEN = os.getenv('TELEGRAM_ACCES_TOKEN', 'your-access-token')

# SECURITY
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key')

def load_public_key(path):
    absolute_path = os.path.join(BASE_DIR, path)
    with open(absolute_path, 'rb') as public_key_file:
        public_key = serialization.load_pem_public_key(public_key_file.read())
    return public_key

def load_private_key(path):
    absolute_path = os.path.join(BASE_DIR, path)
    with open(absolute_path, 'rb') as private_key_file:
        private_key = serialization.load_pem_private_key(
            private_key_file.read(),
            password=None  
        )
    return private_key


PUBLIC_KEY = load_public_key('security/public_key.pem')
PRIVATE_KEY = load_private_key('security/private_key.pem')


# API-KEYS
COINMARKETCAP_APIKEY = os.getenv('COINMARKETCAP_APIKEY', 'coinmarketcap-apikey')
HISTORICAL_FR_API_IP = os.getenv('HISTORICAL_FR_API_IP', 'https//0.0.0.0/')