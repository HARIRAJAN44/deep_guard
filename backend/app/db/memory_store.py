"""
In-memory data store -- replaces MySQL for development / no-DB mode.

Data lives in module-level dicts.  All data is lost on server restart.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

# -- Auto-increment ID counters ------------------------------------------------
_counters: dict[str, int] = {
    "user": 0,
    "api_key": 0,
    "analysis": 0,
    "usage": 0,
    "otp": 0,
}

# -- Data tables ---------------------------------------------------------------
# users: { user_id (str) -> dict }
users: dict[str, dict] = {}
# users_by_email: { email (lowercase) -> user_id (str) }
users_by_email: dict[str, str] = {}
# otps: { (email, purpose) -> dict }
otps: dict[tuple, dict] = {}
# api_keys: { key_id (str) -> dict }
api_keys: dict[str, dict] = {}
# api_keys_by_hash: { key_hash -> key_id (str) }
api_keys_by_hash: dict[str, str] = {}
# analyses: { request_id (str) -> dict }
analyses: dict[str, dict] = {}
# usage: list of dicts
usage: list[dict] = []

_lock = asyncio.Lock()


def _next_id(table: str) -> str:
    _counters[table] += 1
    return str(_counters[table])


# -- User helpers --------------------------------------------------------------

def get_user_by_email(email: str) -> Optional[dict]:
    uid = users_by_email.get(email.lower())
    if uid is None:
        return None
    return users.get(uid)


def get_user_by_id(user_id: str) -> Optional[dict]:
    return users.get(str(user_id))


def create_user(email: str, name: str, password_hash: str) -> str:
    """Insert a new user row. Returns user_id (str)."""
    user_id = _next_id("user")
    now = datetime.now(timezone.utc)
    users[user_id] = {
        "id": user_id,
        "email": email.lower(),
        "name": name.strip(),
        "password_hash": password_hash,
        "email_verified": False,
        "is_active": True,
        "is_admin": False,
        "plan": "free",
        "monthly_limit": 100,
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
    }
    users_by_email[email.lower()] = user_id
    return user_id


def update_user(user_id: str, **kwargs: Any) -> None:
    if user_id in users:
        users[user_id].update(kwargs)
        users[user_id]["updated_at"] = datetime.now(timezone.utc)


# -- OTP helpers ---------------------------------------------------------------

def get_otp(email: str, purpose: str) -> Optional[dict]:
    return otps.get((email.lower(), purpose))


def upsert_otp(email: str, purpose: str, otp_hash: str, expires_at: datetime) -> None:
    now = datetime.now(timezone.utc)
    otps[(email.lower(), purpose)] = {
        "email": email.lower(),
        "purpose": purpose,
        "otp_hash": otp_hash,
        "attempts": 0,
        "created_at": now,
        "expires_at": expires_at,
    }


def increment_otp_attempts(email: str, purpose: str) -> None:
    key = (email.lower(), purpose)
    if key in otps:
        otps[key]["attempts"] += 1


def delete_otp(email: str, purpose: str) -> None:
    otps.pop((email.lower(), purpose), None)


# -- API Key helpers -----------------------------------------------------------

def create_api_key_record(
    user_id: str,
    name: str,
    environment: str,
    prefix: str,
    key_hash: str,
    retention: str,
    allow_model_improvement: bool,
) -> str:
    """Insert a new API key row. Returns key_id (str)."""
    key_id = _next_id("api_key")
    now = datetime.now(timezone.utc)
    api_keys[key_id] = {
        "id": key_id,
        "user_id": str(user_id),
        "name": name,
        "environment": environment,
        "prefix": prefix,
        "key_hash": key_hash,
        "status": "active",
        "retention": retention,
        "allow_model_improvement": allow_model_improvement,
        "policy_version": "1.0",
        "consented_at": now,
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "plan": "free",
        "monthly_limit": 100,
        "requests_this_month": 0,
        "created_at": now,
        "last_used_at": None,
        "revoked_at": None,
    }
    api_keys_by_hash[key_hash] = key_id
    return key_id


def get_api_key_by_hash(key_hash: str) -> Optional[dict]:
    key_id = api_keys_by_hash.get(key_hash)
    if key_id is None:
        return None
    return api_keys.get(key_id)


def get_api_key_by_id(key_id: str) -> Optional[dict]:
    return api_keys.get(str(key_id))


def list_api_keys_for_user(user_id: str) -> list[dict]:
    return sorted(
        [k for k in api_keys.values() if k["user_id"] == str(user_id)],
        key=lambda k: k["created_at"],
        reverse=True,
    )


def update_api_key(key_id: str, **kwargs: Any) -> None:
    if str(key_id) in api_keys:
        api_keys[str(key_id)].update(kwargs)


# -- Analysis helpers ----------------------------------------------------------

def store_analysis(request_id: str, data: dict) -> None:
    analyses[request_id] = data


def get_analysis(request_id: str) -> Optional[dict]:
    return analyses.get(request_id)


def list_analyses_for_user(
    user_id: str,
    assessment_filter: Optional[str] = None,
    api_key_filter: Optional[str] = None,
) -> list[dict]:
    rows = [
        a for a in analyses.values()
        if a.get("user_id") == user_id and a.get("deleted_at") is None
    ]
    if assessment_filter:
        rows = [r for r in rows if r.get("assessment") == assessment_filter]
    if api_key_filter:
        rows = [r for r in rows if r.get("api_key_id") == api_key_filter]
    return sorted(rows, key=lambda r: r.get("created_at", datetime.min), reverse=True)


def soft_delete_analysis(request_id: str) -> None:
    if request_id in analyses:
        analyses[request_id]["deleted_at"] = datetime.now(timezone.utc)
        analyses[request_id]["storage_path"] = None


# -- Usage helpers -------------------------------------------------------------

def record_usage(
    user_id: Optional[str],
    api_key_id: Optional[str],
    request_id: str,
    assessment: str,
    processing_time_ms: int,
    success: bool,
) -> None:
    now = datetime.now(timezone.utc)
    usage.append({
        "id": _next_id("usage"),
        "user_id": user_id,
        "api_key_id": api_key_id,
        "request_id": request_id,
        "assessment": assessment,
        "processing_time_ms": processing_time_ms,
        "success": success,
        "date": now.date().isoformat(),
        "timestamp": now,
    })


def get_usage_for_user(
    user_id: str,
    since: datetime,
    api_key_filter: Optional[str] = None,
) -> list[dict]:
    rows = [
        u for u in usage
        if u.get("user_id") == user_id and u.get("timestamp", datetime.min) >= since
    ]
    if api_key_filter:
        rows = [r for r in rows if r.get("api_key_id") == api_key_filter]
    return sorted(rows, key=lambda r: r.get("timestamp", datetime.min), reverse=True)
