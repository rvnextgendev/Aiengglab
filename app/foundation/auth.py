"""Verify signed JWTs; derive tenant and role from verified claims."""
from dataclasses import dataclass
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import InvalidTokenError
from app.foundation.settings import Settings, get_settings

bearer = HTTPBearer(auto_error=False)
ROLES = {"admin", "editor", "viewer"}

@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    role: str

def verify_token(token: str, settings: Settings) -> Principal:
    try:
        claims = jwt.decode(
            token, settings.jwt_secret.get_secret_value(), algorithms=["HS256"],
            issuer=settings.jwt_issuer, audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "sub", "iss", "aud", "tenant_id", "role"]},
            leeway=10)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token",
                            headers={"WWW-Authenticate": "Bearer"}) from exc
    subject, tenant, role = claims.get("sub"), claims.get("tenant_id"), claims.get("role")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(status_code=401, detail="Invalid subject")
    if not isinstance(tenant, str) or not tenant.strip() or len(tenant) > 80:
        raise HTTPException(status_code=401, detail="Invalid tenant claim")
    if role not in ROLES:
        raise HTTPException(status_code=403, detail="Unrecognized role")
    return Principal(user_id=subject, tenant_id=tenant, role=role)

def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Bearer token required",
                            headers={"WWW-Authenticate": "Bearer"})
    return verify_token(credentials.credentials, settings)

def require_roles(*roles: str):
    def check(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return principal
    return check
