"""FastAPI dependencies: Bearer JWT, admin scope."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette import status

from src.auth.jwt_tokens import decode_access_token

_bearer = HTTPBearer(auto_error=False)


async def require_access_token(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_bearer")
    try:
        return decode_access_token(creds.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token"
        ) from exc


async def require_admin_scope(claims: dict = Depends(require_access_token)) -> dict:
    scope = (claims.get("scope") or "").split()
    if "admin" not in scope:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return claims
