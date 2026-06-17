"""
JWT authentication module.

In production, tokens are issued by an external Identity Provider (IdP)
such as Auth0, Okta, or Azure AD. This module only *verifies* tokens —
it never issues them or trusts user-supplied role claims.

Algorithm: HS256 (shared secret) for local development.
Upgrade path: swap to RS256 by replacing SECRET_KEY with a public key
and changing algorithms=["HS256"] to algorithms=["RS256"].
"""

import os
import sys

import jwt  # PyJWT
from dotenv import load_dotenv

load_dotenv()  # loads JWT_SECRET_KEY from .env if present

VALID_ROLES = {"admin", "hr", "billing", "public"}


# In production this comes from a secrets manager (AWS Secrets Manager, Vault, etc.)
# Never hardcode this or commit it to source control.
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "")


def _require_secret_key() -> None:
    if not SECRET_KEY:
        sys.exit(
            "ERROR: JWT_SECRET_KEY is not set.\n"
            "Add it to your .env file: JWT_SECRET_KEY=your-secret-key\n"
            "Generate a key with: python3 -c \"import secrets; print(secrets.token_hex(32))\""
        )


def verify_token(token: str) -> dict:
    """
    Verify a JWT and return its payload.

    Returns:
        dict with keys: user_id (str), role (str), email (str)

    Raises:
        SystemExit on any verification failure — caller should not catch this.
    """
    _require_secret_key()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        sys.exit("ERROR: Token has expired. Please obtain a new token.")
    except jwt.InvalidTokenError as e:
        sys.exit(f"ERROR: Invalid token — {e}")

    role = payload.get("role", "")
    if role not in VALID_ROLES:
        sys.exit(f"ERROR: Token contains unknown role '{role}'.")

    return {
        "user_id": payload["sub"],
        "role": role,
        "email": payload.get("email", ""),
    }
