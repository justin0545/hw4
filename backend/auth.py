"""Create-account and login for Campus Customs.

Passwords are stored as  pbkdf2_sha256$<salt>$<hash>  in users.password_hash:
  - PBKDF2-HMAC-SHA256, 120,000 iterations (matches the seeded test user)
  - salt: random text, used as its UTF-8 bytes
  - hash: the 32-byte derived key as 64 hex characters
Login never un-hashes anything. It reads the salt out of the stored string,
re-hashes the typed password with that same salt and iteration count, and
compares the two hashes in constant time.

Sessions: on login/signup the server creates a random token, stores only its
SHA-256 in the sessions table, and gives the browser the token in an HttpOnly
cookie that page JavaScript can't read.
"""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from db import connect_rw

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 120_000
SALT_BYTES = 16  # becomes 32 hex characters of salt text

SESSION_COOKIE = "cc_session"
SESSION_DAYS = 7
# Set COOKIE_SECURE=1 when served over HTTPS; localhost dev runs on plain HTTP.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE") == "1"

# Brute-force throttle: this many failed logins per email+IP within the window
# locks out further attempts until the window passes.
MAX_FAILURES = 5
FAILURE_WINDOW_SECONDS = 15 * 60

MIN_PASSWORD_LENGTH = 8
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---- Password hashing -------------------------------------------------------

def _pbkdf2(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), ITERATIONS).hex()


def hash_password(password: str) -> str:
    """For signup: new random salt, then the stored string."""
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${salt}${_pbkdf2(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    """For login: reuse the stored salt, re-hash, constant-time compare."""
    try:
        algorithm, salt, expected = stored.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    return hmac.compare_digest(_pbkdf2(password, salt), expected)


# Checked when the email doesn't exist, so a wrong email takes as long as a
# wrong password and response time doesn't reveal which accounts exist.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# ---- Sessions ---------------------------------------------------------------

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def init_auth_tables() -> None:
    with connect_rw() as con:
        con.execute(
            """create table if not exists sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )"""
        )
        con.execute("delete from sessions where expires_at < datetime('now')")


def _start_session(response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    with connect_rw() as con:
        con.execute(
            "insert into sessions (token_hash, user_id, expires_at) values (?, ?, ?)",
            (_token_hash(token), user_id, expires.strftime("%Y-%m-%d %H:%M:%S")),
        )
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_DAYS * 86400,
        httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/",
    )


def current_user(request: Request) -> dict | None:
    """The logged-in user for this request, or None. Problem 5's chat will use this."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    with connect_rw() as con:
        row = con.execute(
            "select u.id, u.first_name, u.last_name, u.name, u.email, u.created_at as member_since from sessions s "
            "join users u on u.id = s.user_id "
            "where s.token_hash = ? and s.expires_at > datetime('now')",
            (_token_hash(token),),
        ).fetchone()
    return dict(row) if row else None


# ---- Login throttle ---------------------------------------------------------

_failures: dict[str, deque[float]] = defaultdict(deque)


def _throttle_key(request: Request, email: str) -> str:
    return f"{request.client.host if request.client else '?'}|{email}"


def _recent_failures(key: str) -> deque[float]:
    q = _failures[key]
    cutoff = time.monotonic() - FAILURE_WINDOW_SECONDS
    while q and q[0] < cutoff:
        q.popleft()
    return q


# ---- API --------------------------------------------------------------------

class SignupIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)
    confirm_password: str = Field(max_length=256)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", status_code=201)
def signup(body: SignupIn, response: Response) -> dict:
    first, last = body.first_name.strip(), body.last_name.strip()
    email = body.email.strip().lower()
    if not first or not last:
        raise HTTPException(422, "Please enter your first and last name.")
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Please enter a valid email address.")
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(422, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if body.password != body.confirm_password:
        raise HTTPException(422, "Passwords don't match.")

    taken = HTTPException(409, "An account with this email already exists. Try logging in.")
    with connect_rw() as con:
        if con.execute("select 1 from users where email = ?", (email,)).fetchone():
            raise taken
        try:
            cur = con.execute(
                "insert into users (name, email, password_hash, first_name, last_name) values (?, ?, ?, ?, ?)",
                (f"{first} {last}", email, hash_password(body.password), first, last),
            )
        except sqlite3.IntegrityError:  # same email signed up at the same moment
            raise taken
        user_id = cur.lastrowid
    _start_session(response, user_id)
    return {"id": user_id, "first_name": first, "last_name": last, "name": f"{first} {last}", "email": email}


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response) -> dict:
    email = body.email.strip().lower()
    key = _throttle_key(request, email)
    if len(_recent_failures(key)) >= MAX_FAILURES:
        raise HTTPException(429, "Too many failed attempts. Please wait 15 minutes and try again.")

    with connect_rw() as con:
        row = con.execute(
            "select id, first_name, last_name, name, email, password_hash from users where email = ?", (email,)
        ).fetchone()
    ok = verify_password(body.password, row["password_hash"] if row else _DUMMY_HASH) and row is not None
    if not ok:
        _failures[key].append(time.monotonic())
        # Same message whether the email or the password was wrong.
        raise HTTPException(401, "Incorrect email or password.")

    _failures.pop(key, None)
    _start_session(response, row["id"])
    user = dict(row)
    del user["password_hash"]
    return user


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        with connect_rw() as con:
            con.execute("delete from sessions where token_hash = ?", (_token_hash(token),))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Not logged in.")
    return user
