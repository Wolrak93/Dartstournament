import os

import jwt

_SECRET = os.getenv("MOBILE_JWT_SECRET", "backsberger-open-dev-secret-key-2024")
_ALGORITHM = "HS256"


def create_mobile_token(player_id: int, name: str) -> str:
    return jwt.encode({"sub": str(player_id), "name": name}, _SECRET, algorithm=_ALGORITHM)


def verify_mobile_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
