"""Password and client secret hashing (Argon2)."""

from passlib.context import CryptContext

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def hash_secret(plain: str) -> str:
    return _pwd.hash(plain)


def verify_secret(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)
