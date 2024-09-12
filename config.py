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
DB_USER = os.getenv('DB_USERNAME', 'username')
DB_PASS = os.getenv('DB_PASS', 'password')
DB_HOST = os.getenv('DB_HOST', '0.0.0.0')