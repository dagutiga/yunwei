import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


class SecretError(Exception):
    """Raised when secret encryption/decryption fails."""


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    key = os.getenv("SSH_SECRET_KEY")
    if not key:
        raise SecretError("缺少 SSH_SECRET_KEY 配置")

    try:
        return Fernet(key.encode("utf-8"))
    except Exception as exc:
        raise SecretError("SSH_SECRET_KEY 格式无效") from exc


def encrypt_secret(plain_text: str) -> str:
    try:
        return _get_fernet().encrypt(plain_text.encode("utf-8")).decode("utf-8")
    except SecretError:
        raise
    except Exception as exc:
        raise SecretError("敏感数据加密失败") from exc


def decrypt_secret(cipher_text: str) -> str:
    try:
        return _get_fernet().decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except SecretError:
        raise
    except InvalidToken as exc:
        raise SecretError("敏感数据解密失败") from exc
    except Exception as exc:
        raise SecretError("敏感数据解密失败") from exc
