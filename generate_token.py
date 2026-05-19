"""
Development token generator — simulates what an IdP would issue.

DO NOT use this in production. In production, tokens come from your
Identity Provider (Auth0, Okta, Azure AD, etc.) after real credential
verification.

Usage:
    python generate_token.py --role hr --user alice --email alice@medcare.com
    python generate_token.py --role admin --user bob --email bob@medcare.com
    python generate_token.py --list-roles
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import jwt  # PyJWT

VALID_ROLES = {"admin", "hr", "billing", "public"}
DEFAULT_EXPIRY_HOURS = 8


def main():
    parser = argparse.ArgumentParser(description="Generate a dev JWT for local testing.")
    parser.add_argument("--role", choices=sorted(VALID_ROLES), help="Role to embed in the token")
    parser.add_argument("--user", default="dev-user", help="User ID (sub claim)")
    parser.add_argument("--email", default="", help="Email address")
    parser.add_argument("--expires-in", type=int, default=DEFAULT_EXPIRY_HOURS,
                        help=f"Token lifetime in hours (default: {DEFAULT_EXPIRY_HOURS})")
    parser.add_argument("--list-roles", action="store_true", help="List available roles and exit")
    args = parser.parse_args()

    if args.list_roles:
        print("Available roles:", ", ".join(sorted(VALID_ROLES)))
        return

    if not args.role:
        parser.error("--role is required")

    secret_key = os.environ.get("JWT_SECRET_KEY", "")
    if not secret_key:
        sys.exit(
            "ERROR: JWT_SECRET_KEY environment variable is not set.\n"
            "Example: export JWT_SECRET_KEY=$(python -c \"import secrets; print(secrets.token_hex(32))\")"
        )

    now = datetime.now(timezone.utc)
    payload = {
        "sub": args.user,
        "email": args.email,
        "role": args.role,
        "iat": now,
        "exp": now + timedelta(hours=args.expires_in),
    }

    token = jwt.encode(payload, secret_key, algorithm="HS256")

    expiry = (now + timedelta(hours=args.expires_in)).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\nToken for '{args.user}' (role: {args.role}, expires: {expiry}):\n")
    print(token)
    print(f"\nTo use:\n  export AUTH_TOKEN='{token}'")
    print(f"  python main.py")


if __name__ == "__main__":
    main()
