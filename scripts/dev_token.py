"""Local development only: create short-lived HS256 JWT for manual testing."""
import argparse
from datetime import datetime, timedelta, timezone
import jwt
from app.foundation.settings import get_settings

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--role", choices=["admin", "editor", "viewer"], default="viewer")
    parser.add_argument("--user", default="local-user")
    args = parser.parse_args()
    settings = get_settings()
    if settings.app_env != "development":
        raise SystemExit("Dev token generator only works with APP_ENV=development")
    now = datetime.now(timezone.utc)
    token = jwt.encode({
        "sub": args.user, "tenant_id": args.tenant, "role": args.role,
        "iss": settings.jwt_issuer, "aud": settings.jwt_audience,
        "iat": now, "exp": now + timedelta(minutes=15)
    }, settings.jwt_secret.get_secret_value(), algorithm="HS256")
    print(token)

if __name__ == "__main__":
    main()
