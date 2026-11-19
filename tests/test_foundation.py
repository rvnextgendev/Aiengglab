"""Offline identity and configuration tests."""
from datetime import datetime, timedelta, timezone
import jwt
import pytest
from fastapi import HTTPException
from app.foundation.settings import Settings
from app.foundation.auth import verify_token

SECRET = "local-test-secret-with-at-least-32-characters"

def settings():
    return Settings(_env_file=None, jwt_secret=SECRET, app_env="test")

def token(tenant="tenant-a", role="viewer", expires=5):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": "user-1", "tenant_id": tenant, "role": role,
                       "iss": "arinova-local", "aud": "arinova-api",
                       "iat": now, "exp": now + timedelta(minutes=expires)},
                      SECRET, algorithm="HS256")

def test_valid_identity():
    principal = verify_token(token(), settings())
    assert principal.tenant_id == "tenant-a"
    assert principal.role == "viewer"

def test_expired_token_rejected():
    with pytest.raises(HTTPException) as exc:
        verify_token(token(expires=-5), settings())
    assert exc.value.status_code == 401

def test_invalid_signature_rejected():
    with pytest.raises(HTTPException):
        verify_token(token() + "tampered", settings())

def test_missing_tenant_rejected():
    claims = jwt.decode(token(), SECRET, algorithms=["HS256"], audience="arinova-api", issuer="arinova-local")
    claims.pop("tenant_id")
    with pytest.raises(HTTPException):
        verify_token(jwt.encode(claims, SECRET, algorithm="HS256"), settings())

def test_short_secret_rejected():
    with pytest.raises(ValueError):
        Settings(_env_file=None, jwt_secret="short", app_env="test")
