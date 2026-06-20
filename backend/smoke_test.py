"""End-to-end API smoke test for ContentFlow.

Exercises the critical flows the web + mobile apps depend on, against a RUNNING
backend (default http://localhost:8000). Prints PASS/FAIL per step.

Usage:
    cd backend
    python smoke_test.py                 # tests http://localhost:8000
    BASE_URL=http://localhost:8000 python smoke_test.py

Requires: httpx (already a backend dependency).
"""
from __future__ import annotations

import os
import random
import sys

import httpx

BASE = os.environ.get("BASE_URL", "http://localhost:8000")
PASS, FAIL = "\033[92mPASS\033[0m", "\033[91mFAIL\033[0m"
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    results.append((ok, label))
    print(f"  [{PASS if ok else FAIL}] {label}" + (f"  — {detail}" if detail else ""))


def main() -> int:
    email = f"smoke_{random.randint(100000, 999999)}@example.com"
    pwd = "SmokeTest123!"
    print(f"\nSmoke testing {BASE}\nTest user: {email}\n")

    with httpx.Client(base_url=BASE, timeout=90) as c:
        # 1. health
        try:
            r = c.get("/health")
            check(r.status_code == 200, "GET /health", f"{r.status_code}")
        except Exception as e:
            check(False, "GET /health", repr(e))
            print("\nBackend not reachable — start it first. Aborting.")
            return 1

        # 2. register
        r = c.post("/api/v1/auth/register", json={"email": email, "password": pwd, "name": "Smoke Test"})
        token = r.json().get("access_token") if r.status_code == 201 else None
        check(r.status_code == 201 and bool(token), "register -> 201 + token", f"{r.status_code}")
        if not token:
            print("\nCannot continue without a token.")
            return 1
        H = {"Authorization": f"Bearer {token}"}

        # 3. /me  (shape: { user: {...} })
        r = c.get("/api/v1/auth/me", headers=H)
        me_ok = r.status_code == 200 and bool(r.json().get("user", {}).get("email"))
        check(me_ok, "GET /auth/me -> user.email", f"{r.status_code}")

        # 4. content feed
        r = c.get("/api/v1/content-projects?page_size=50", headers=H)
        feed_ok = r.status_code == 200 and isinstance(r.json().get("items"), list)
        check(feed_ok, "GET /content-projects -> items[]", f"{r.status_code}")

        # 5. dashboard usage
        r = c.get("/api/v1/billing/usage", headers=H)
        usage_ok = r.status_code == 200 and "posts_limit" in r.json()
        check(usage_ok, "GET /billing/usage", f"{r.status_code}")

        # 6. AI repurpose (real LLM — needs OPENAI/GEMINI key configured)
        r = c.post("/api/v1/ai/repurpose", headers=H, json={
            "source_text": "I built an AI tool that schedules content. 3 lessons on shipping fast.",
            "platforms": ["instagram", "x", "linkedin"],
            "tone": "professional",
        })
        if r.status_code == 200:
            n = len(r.json().get("variants", []))
            check(n > 0, "POST /ai/repurpose -> variants", f"{n} variants")
        elif r.status_code == 503:
            check(True, "POST /ai/repurpose (skipped — AI not configured)", "503")
        else:
            check(False, "POST /ai/repurpose", f"{r.status_code}: {r.text[:120]}")

        # 7. login
        r = c.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        check(r.status_code == 200 and bool(r.json().get("access_token")), "login -> token", f"{r.status_code}")

        # 8. brute-force lockout (8 wrong attempts -> locked)
        for _ in range(8):
            c.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass!"})
        r = c.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        locked = r.status_code == 401 and "Too many" in (r.json().get("message", "") + r.json().get("detail", ""))
        check(locked, "login lockout after 8 fails (correct pwd blocked)", f"{r.status_code}")

    ok = sum(1 for r, _ in results if r)
    total = len(results)
    print(f"\n{'='*48}\n{ok}/{total} checks passed\n")
    return 0 if ok == total else 2


if __name__ == "__main__":
    sys.exit(main())
