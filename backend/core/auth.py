try:
    # 优先使用bcrypt
    import bcrypt
    BCRYPT_MODE = True
except ImportError:
    # 备用passlib
    from passlib.hash import bcrypt
    BCRYPT_MODE = False

from .logger import log

def encrypt_password(password: str) -> str:
    """加密密码（兼容bcrypt/passlib）"""
    if BCRYPT_MODE:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    else:
        return bcrypt.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（兼容bcrypt/passlib）"""
    try:
        if BCRYPT_MODE:
            plain_bytes = plain_password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(plain_bytes, hashed_bytes)
        else:
            return bcrypt.verify(plain_password, hashed_password)
    except Exception as e:
        log.error(f"密码验证失败: {e}, 哈希长度: {len(hashed_password)}")
        return False
