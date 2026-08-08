"""
THEeye - Authentication Module
User registration, login, and session token management.

Uses PBKDF2-HMAC-SHA256 for password hashing (built-in, no extra dependencies).
Tokens are UUID-based and stored in memory (use a database for production).
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class User:
    """Internal user representation (includes password hash)."""
    id: str
    email: str
    name: str
    password_hash: str
    salt: str
    created_at: str
    institution: str = ""
    research_field: str = ""
    role: str = "user"  # "user" or "admin"
    is_active: bool = True


# In-memory stores (use a database for production)
_users: dict[str, User] = {}        # email -> User
_tokens: dict[str, str] = {}        # token -> user_id
_user_by_id: dict[str, User] = {}   # id -> User


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Hash a password using PBKDF2-HMAC-SHA256. Returns (hash_hex, salt_hex)."""
    if salt is None:
        salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return key.hex(), salt.hex()


def _verify_password(password: str, stored_hash: str, salt_hex: str) -> bool:
    """Verify a password against the stored hash and salt."""
    salt = bytes.fromhex(salt_hex)
    key, _ = _hash_password(password, salt)
    return secrets.compare_digest(key, stored_hash)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_user(email: str, password: str, name: str,
                  institution: str = "", research_field: str = "") -> dict:
    """
    Register a new user.

    Returns: {"user": user_info, "token": token} on success.
    Raises: ValueError if email already registered or password too weak.
    """
    email = email.lower().strip()
    if email in _users:
        raise ValueError("An account with this email already exists.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    password_hash, salt = _hash_password(password)
    user_id = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()

    user = User(
        id=user_id,
        email=email,
        name=name.strip(),
        password_hash=password_hash,
        salt=salt,
        created_at=now,
        institution=institution.strip(),
        research_field=research_field.strip(),
    )

    _users[email] = user
    _user_by_id[user_id] = user

    token = _create_token(user_id)
    return {"user": _user_to_public(user), "token": token}


def login_user(email: str, password: str) -> dict:
    """
    Authenticate a user.

    Returns: {"user": user_info, "token": token} on success.
    Raises: ValueError if credentials are invalid.
    """
    email = email.lower().strip()
    user = _users.get(email)
    if not user:
        raise ValueError("Invalid email or password.")
    if not _verify_password(password, user.password_hash, user.salt):
        raise ValueError("Invalid email or password.")
    if not user.is_active:
        raise ValueError("This account has been deactivated. Contact the administrator.")

    token = _create_token(user.id)
    return {"user": _user_to_public(user), "token": token}


def verify_token(token: str) -> User | None:
    """Verify a session token and return the associated user, or None."""
    if not token:
        return None
    user_id = _tokens.get(token)
    if not user_id:
        return None
    return _user_by_id.get(user_id)


def logout_user(token: str) -> bool:
    """Invalidate a session token."""
    if token in _tokens:
        del _tokens[token]
        return True
    return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _create_token(user_id: str) -> str:
    """Create a new session token for a user."""
    token = secrets.token_urlsafe(32)
    _tokens[token] = user_id
    return token


def _user_to_public(user: User) -> dict:
    """Convert a User to a public dict (no password info)."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "institution": user.institution,
        "research_field": user.research_field,
        "created_at": user.created_at,
        "role": user.role,
        "is_active": user.is_active,
    }


def is_admin(user: User) -> bool:
    """Check if a user has admin role."""
    return user.role == "admin"


def get_all_users() -> list[dict]:
    """Return all registered users (public info only)."""
    return [_user_to_public(u) for u in _users.values()]


def get_user_by_id(user_id: str) -> dict | None:
    """Get a user by ID (public info)."""
    user = _user_by_id.get(user_id)
    if not user:
        return None
    return _user_to_public(user)


def update_user_role(user_id: str, role: str) -> dict:
    """Update a user's role. Only 'user' and 'admin' are valid."""
    if role not in ("user", "admin"):
        raise ValueError("Invalid role. Must be 'user' or 'admin'.")
    user = _user_by_id.get(user_id)
    if not user:
        raise ValueError("User not found.")
    user.role = role
    return _user_to_public(user)


def toggle_user_active(user_id: str) -> dict:
    """Toggle a user's active status."""
    user = _user_by_id.get(user_id)
    if not user:
        raise ValueError("User not found.")
    user.is_active = not user.is_active
    return _user_to_public(user)


def delete_user(user_id: str) -> bool:
    """Delete a user account."""
    user = _user_by_id.get(user_id)
    if not user:
        raise ValueError("User not found.")
    # Invalidate all tokens for this user
    tokens_to_remove = [t for t, uid in _tokens.items() if uid == user_id]
    for t in tokens_to_remove:
        del _tokens[t]
    # Remove from stores
    del _users[user.email]
    del _user_by_id[user_id]
    return True


def update_user_profile(user_id: str, name: str = None, institution: str = None,
                        research_field: str = None) -> dict:
    """Update a user's profile fields."""
    user = _user_by_id.get(user_id)
    if not user:
        raise ValueError("User not found.")
    if name is not None:
        user.name = name.strip()
    if institution is not None:
        user.institution = institution.strip()
    if research_field is not None:
        user.research_field = research_field.strip()
    return _user_to_public(user)


def change_password(user_id: str, old_password: str, new_password: str) -> bool:
    """Change a user's password."""
    user = _user_by_id.get(user_id)
    if not user:
        raise ValueError("User not found.")
    if not _verify_password(old_password, user.password_hash, user.salt):
        raise ValueError("Current password is incorrect.")
    if len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters.")
    user.password_hash, user.salt = _hash_password(new_password)
    return True


def admin_reset_password(user_id: str, new_password: str) -> bool:
    """Admin-only: reset any user's password."""
    user = _user_by_id.get(user_id)
    if not user:
        raise ValueError("User not found.")
    if len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters.")
    user.password_hash, user.salt = _hash_password(new_password)
    return True


# Create default accounts for easy testing
def _init_demo_users():
    """Create demo and admin accounts for quick testing."""
    # Demo user
    demo_email = "demo@theeye.local"
    if demo_email not in _users:
        register_user(
            email=demo_email,
            password="demo123",
            name="Demo Researcher",
            institution="THEeye Demo",
            research_field="Economics",
        )

    # Admin user
    admin_email = "admin@theeye.local"
    if admin_email not in _users:
        result = register_user(
            email=admin_email,
            password="admin123",
            name="THEeye Administrator",
            institution="THEeye Platform",
            research_field="Administration",
        )
        # Promote to admin
        admin_user = _user_by_id.get(result["user"]["id"])
        if admin_user:
            admin_user.role = "admin"

_init_demo_users()
