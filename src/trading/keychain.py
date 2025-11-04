"""
Helper utilities to interact with the OS keychain via the 'keyring' package.

Provides a safe helper to load secrets from the OS keyring into process
environment variables. This keeps secrets out of plaintext files and allows
developers to store credentials in Windows Credential Manager / macOS Keychain
or other backends supported by keyring.
"""
from typing import Iterable
import os
import logging

LOGGER = logging.getLogger(__name__)


def load_secrets_into_env(keys: Iterable[str], service_name: str = 'daily_trading_bot') -> dict:
    """Try to read each key from the OS keyring and set it into os.environ.

    Returns a dict of {key: value_or_None} for all requested keys.
    """
    try:
        import keyring
    except Exception:
        LOGGER.debug('keyring 패키지 없음; 키체인에서 값을 읽을 수 없습니다')
        return {k: None for k in keys}

    result = {}
    for k in keys:
        try:
            val = keyring.get_password(service_name, k)
            if val:
                os.environ[k] = str(val)
            result[k] = val
        except Exception as e:
            LOGGER.exception('키체인에서 %s 읽기 실패: %s', k, e)
            result[k] = None
    return result


def set_secret_in_keyring(key: str, value: str, service_name: str = 'daily_trading_bot') -> bool:
    """Set a secret into the OS keyring. Returns True on success.
    """
    try:
        import keyring
        keyring.set_password(service_name, key, value)
        return True
    except Exception as e:
        LOGGER.exception('키체인에 %s 설정 실패: %s', key, e)
        return False
