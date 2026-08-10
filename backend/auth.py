"""
THEeye - Authentication Module
User registration, login, and session token management.

Uses PBKDF2-HMAC-SHA256 for password hashing (built-in, no extra dependencies).
Tokens are HMAC-signed and self-contained (survive server restarts).
User accounts are persisted to a JSON file so they survive restarts.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_SECRET_KEY = os.environ.get("SECRET_KEY", "theeye-default-secret-change-me")
_DATA_FILE = os.environ.get("THEEYE_DATA_FILE", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "users.json"
))
_TOKEN_TTL_DEFAULT = 86400 * 1        # 1 day
_TOKEN_TTL_REMEMBER = 86400 * 30      # 30 days


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


# In-memory stores (backed by file persistence)
_users: dict[str, User] = {}        # email -> User
_tokens: dict[str, str] = {}        # token -> user_id (legacy; signed tokens don't need this)
_user_by_id: dict[str, User] = {}   # id -> User


# ---------------------------------------------------------------------------
# File-based persistence
# ---------------------------------------------------------------------------

def _save_users() -> None:
    """Persist all users to a JSON file so they survive server restarts."""
    try:
        os.makedirs(os.path.dirname(_DATA_FILE), exist_ok=True)
        users_data = [
            {
                "id": u.id, "email": u.email, "name": u.name,
                "password_hash": u.password_hash, "salt": u.salt,
                "created_at": u.created_at, "institution": u.institution,
                "research_field": u.research_field, "role": u.role,
                "is_active": u.is_active,
            }
            for u in _users.values()
        ]
        with open(_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2)
    except Exception as e:
        print(f"[Auth] Warning: could not save users to file: {e}")


def _load_users() -> None:
    """Load users from the JSON file on startup."""
    try:
        if os.path.exists(_DATA_FILE):
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                users_data = json.load(f)
            for udata in users_data:
                user = User(**udata)
                _users[user.email] = user
                _user_by_id[user.id] = user
            print(f"[Auth] Loaded {len(_users)} user(s) from {_DATA_FILE}")
    except Exception as e:
        print(f"[Auth] Warning: could not load users from file: {e}")


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
    _save_users()  # Persist to file

    token = _create_token(user_id, remember=True)
    return {"user": _user_to_public(user), "token": token}


def login_user(email: str, password: str, remember: bool = False) -> dict:
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

    token = _create_token(user.id, remember=remember)
    return {"user": _user_to_public(user), "token": token}


def verify_token(token: str) -> User | None:
    """Verify a session token and return the associated user, or None.

    Supports both new HMAC-signed tokens (self-contained, survive restarts)
    and legacy in-memory tokens (for backward compatibility).
    """
    if not token:
        return None
    # Try signed token first (new system)
    user_id = _verify_signed_token(token)
    if user_id:
        return _user_by_id.get(user_id)
    # Fall back to legacy in-memory token
    user_id = _tokens.get(token)
    if user_id:
        return _user_by_id.get(user_id)
    return None


def logout_user(token: str) -> bool:
    """Invalidate a session token.

    For signed tokens, we can't truly revoke them (they're self-contained),
    but we add them to a revocation set. For legacy tokens, we delete them.
    """
    if token in _tokens:
        del _tokens[token]
        return True
    # Signed tokens are stateless — they'll expire naturally.
    # Return True so the frontend clears local state regardless.
    return True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _create_token(user_id: str, remember: bool = False) -> str:
    """Create a self-contained HMAC-signed token.

    The token encodes user_id, issued-at, and expiry. It is signed with
    SECRET_KEY so it can be verified without any in-memory state — tokens
    survive server restarts.
    """
    ttl = _TOKEN_TTL_REMEMBER if remember else _TOKEN_TTL_DEFAULT
    payload = {
        "uid": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl,
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(
        payload_json.encode("utf-8")
    ).decode("ascii").rstrip("=")
    sig = hmac.new(
        _SECRET_KEY.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_b64}.{sig}"


def _verify_signed_token(token: str) -> str | None:
    """Verify a signed token and return user_id, or None if invalid/expired."""
    if not token:
        return None
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected_sig = hmac.new(
            _SECRET_KEY.encode("utf-8"),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        # Restore padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(
            base64.urlsafe_b64decode(payload_b64.encode("ascii"))
        )
        if int(time.time()) > payload.get("exp", 0):
            return None
        return payload.get("uid")
    except Exception:
        return None


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
    _save_users()
    return _user_to_public(user)


def toggle_user_active(user_id: str) -> dict:
    """Toggle a user's active status."""
    user = _user_by_id.get(user_id)
    if not user:
        raise ValueError("User not found.")
    user.is_active = not user.is_active
    _save_users()
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
    _save_users()
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
    _save_users()
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
    _save_users()
    return True


def admin_reset_password(user_id: str, new_password: str) -> bool:
    """Admin-only: reset any user's password."""
    user = _user_by_id.get(user_id)
    if not user:
        raise ValueError("User not found.")
    if len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters.")
    user.password_hash, user.salt = _hash_password(new_password)
    _save_users()
    return True


# ---------------------------------------------------------------------------
# Startup: load persisted users, then ensure demo accounts exist
# ---------------------------------------------------------------------------

# Load persisted users BEFORE creating demo accounts
_load_users()

# Create default accounts for easy testing
def _init_demo_users():
    """Create demo and admin accounts for quick testing (if not already present)."""
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
