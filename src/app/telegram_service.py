import hashlib
import hmac

from src.config import TELEGRAM_ACCES_TOKEN



async def verify_telegram_oauth(data: dict) -> bool:
    """
    Verifies the authenticity of the Telegram login data.
    """
    auth_data = {k: v for k, v in data.items() if k != 'hash'}
    data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(auth_data.items())])
    secret_key = hashlib.sha256(TELEGRAM_ACCES_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return computed_hash == data.get('hash')
