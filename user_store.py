import os
import sqlite3
from contextlib import contextmanager

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")
_ph = PasswordHasher()


@contextmanager
def _db():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create the users table if it doesn't exist."""
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username      TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL,
                email         TEXT NOT NULL,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def add_user(username: str, password: str, role: str, email: str) -> None:
    """Add a new user. Raises sqlite3.IntegrityError if username already exists."""
    with _db() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, email) VALUES (?, ?, ?, ?)",
            (username.lower().strip(), _ph.hash(password), role, email),
        )


def authenticate(username: str, password: str) -> dict | None:
    """Verify credentials. Returns identity dict on success, None on failure."""
    with _db() as conn:
        row = conn.execute(
            "SELECT password_hash, role, email FROM users WHERE username = ?",
            (username.lower().strip(),),
        ).fetchone()

    if not row:
        return None

    try:
        _ph.verify(row["password_hash"], password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return None

    # Transparently rehash if Argon2 parameters have been upgraded
    if _ph.check_needs_rehash(row["password_hash"]):
        _update_hash(username, _ph.hash(password))

    return {"user_id": username.lower().strip(), "role": row["role"], "email": row["email"]}


def update_password(username: str, new_password: str) -> None:
    """Replace a user's password hash."""
    _update_hash(username.lower().strip(), _ph.hash(new_password))


def _update_hash(username: str, new_hash: str) -> None:
    with _db() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (new_hash, username),
        )


def delete_user(username: str) -> None:
    """Remove a user from the database."""
    with _db() as conn:
        conn.execute("DELETE FROM users WHERE username = ?", (username.lower().strip(),))


def list_users() -> list[dict]:
    """Return all users (excluding password hashes)."""
    with _db() as conn:
        rows = conn.execute(
            "SELECT username, role, email, created_at FROM users ORDER BY username"
        ).fetchall()
    return [dict(row) for row in rows]
