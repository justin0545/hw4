"""Auth checks, run against a throwaway copy of the seed database.

    cd backend && python test_auth.py
"""
import os as _os, tempfile as _tf; _os.environ.setdefault("CAMPUS_CUSTOMS_AUDIT", _os.path.join(_tf.mkdtemp(), "audit_trail.json"))  # tests never touch the real audit trail

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The untouched original database: the backup made in Problem 4 if present, otherwise the
# data pack's campus_customs.db (what a grader has after unzipping data.zip).
SEED_DB = next(p for p in (ROOT / "data" / "campus_customs.seed.db", ROOT / "data" / "campus_customs.db") if p.exists())
tmp = Path(tempfile.mkdtemp()) / "test.db"
shutil.copy(SEED_DB, tmp)
os.environ["CAMPUS_CUSTOMS_DB"] = str(tmp)

from fastapi.testclient import TestClient  # noqa: E402

from auth import ITERATIONS, hash_password, verify_password  # noqa: E402
from main import app  # noqa: E402

SEED_EMAIL, SEED_PASSWORD = "test@campuscustoms.yale.edu", "password"
results = []


def check(name: str, cond: bool) -> None:
    results.append(cond)
    print(("PASS " if cond else "FAIL ") + name)


# Hash function on its own
h = hash_password("correct horse battery")
algo, salt, digest = h.split("$")
check("new hash has pbkdf2_sha256$salt$hash format", algo == "pbkdf2_sha256" and len(salt) == 32 and len(digest) == 64)
check("120,000 iterations", ITERATIONS == 120_000)
check("same password hashes differently each time (random salt)", hash_password("x" * 10) != hash_password("x" * 10))
check("verify accepts right password", verify_password("correct horse battery", h))
check("verify rejects wrong password", not verify_password("correct horse batterY", h))

with TestClient(app) as c:
    # Seeded test user
    r = c.post("/api/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD})
    check("seed user logs in", r.status_code == 200 and r.json()["email"] == SEED_EMAIL)
    check("login response has no password_hash", "password_hash" not in r.json())
    check("session cookie is HttpOnly", "httponly" in r.headers.get("set-cookie", "").lower())
    check("/me returns seed user", c.get("/api/auth/me").json().get("first_name") == "Test")
    c.post("/api/auth/logout")
    check("/me is 401 after logout", c.get("/api/auth/me").status_code == 401)
    check("seed user wrong password rejected", c.post("/api/auth/login", json={"email": SEED_EMAIL, "password": "Password"}).status_code == 401)
    check("email is case-insensitive", c.post("/api/auth/login", json={"email": SEED_EMAIL.upper(), "password": SEED_PASSWORD}).status_code == 200)
    c.post("/api/auth/logout")

    # Brand-new account through the API
    new = {"first_name": "Handsome", "last_name": "Dan", "email": "handsome.dan@example.test",
           "password": "BoolaBoola2026", "confirm_password": "BoolaBoola2026"}
    r = c.post("/api/auth/signup", json=new)
    check("signup succeeds", r.status_code == 201)
    check("signup logs you in", c.get("/api/auth/me").json().get("email") == new["email"])
    c.post("/api/auth/logout")
    r = c.post("/api/auth/login", json={"email": new["email"], "password": new["password"]})
    check("new account logs in", r.status_code == 200 and r.json()["name"] == "Handsome Dan")
    c.post("/api/auth/logout")
    check("new account wrong password rejected", c.post("/api/auth/login", json={"email": new["email"], "password": "boolaboola2026"}).status_code == 401)

    # Signup validation
    check("duplicate email rejected (409)", c.post("/api/auth/signup", json=new).status_code == 409)
    check("mismatched confirm rejected", c.post("/api/auth/signup", json={**new, "email": "a@b.test", "confirm_password": "nope12345"}).status_code == 422)
    check("short password rejected", c.post("/api/auth/signup", json={**new, "email": "a@b.test", "password": "short", "confirm_password": "short"}).status_code == 422)
    check("bad email rejected", c.post("/api/auth/signup", json={**new, "email": "not-an-email"}).status_code == 422)

    # Unknown email gets the same message as a wrong password
    r1 = c.post("/api/auth/login", json={"email": "nobody@example.test", "password": "whatever1"})
    r2 = c.post("/api/auth/login", json={"email": new["email"], "password": "whatever1"})
    check("unknown email and wrong password look identical", r1.status_code == r2.status_code == 401 and r1.json() == r2.json())

    # Throttle: 5 failures, then locked out even with the right password
    for _ in range(5):
        c.post("/api/auth/login", json={"email": SEED_EMAIL, "password": "guess"})
    check("locked out after 5 failures", c.post("/api/auth/login", json={"email": SEED_EMAIL, "password": SEED_PASSWORD}).status_code == 429)

# What actually got stored
con = sqlite3.connect(tmp)
stored = con.execute("select password_hash from users where email = ?", (new["email"],)).fetchone()[0]
check("plaintext password is not in the database", new["password"] not in stored and new["password"].encode() not in tmp.read_bytes())
check("stored hash verifies with the shared function", verify_password(new["password"], stored))
check("sessions table stores token hashes, not raw cookies", all(len(t) == 64 for (t,) in con.execute("select token_hash from sessions")))
con.close()

print(f"\n{sum(results)}/{len(results)} passed")
raise SystemExit(0 if all(results) else 1)
