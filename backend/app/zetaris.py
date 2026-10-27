"""Zetaris data layer client: login, then read-only SQL through the platform's SQL editor API."""
import httpx
from app.config import settings

TIMEOUT = 30.0


class ZetarisError(RuntimeError):
    pass


def configured() -> bool:
    return bool(settings.ZETARIS_BASE_URL and settings.ZETARIS_USERNAME and settings.ZETARIS_PASSWORD and not settings.SAMPLE_MODE)


def _token(client: httpx.Client) -> str:
    r = client.post(f"{settings.ZETARIS_BASE_URL.rstrip('/')}/api/auth/login",
                    json={"username": settings.ZETARIS_USERNAME, "password": settings.ZETARIS_PASSWORD})
    if r.status_code != 200 or not r.json().get("idToken"):
        raise ZetarisError(f"Zetaris login failed: HTTP {r.status_code}")
    return r.json()["idToken"]


def run_sql(sql: str, limit: int = 500) -> list[dict]:
    """Executes one statement and returns rows as dicts (Zetaris returns {headers, data})."""
    if not configured():
        raise ZetarisError("Zetaris is not configured")
    with httpx.Client(timeout=TIMEOUT) as client:
        headers = {"authorization": f"Bearer {_token(client)}", "x-org-id": settings.ZETARIS_ORG_ID}
        r = client.post(f"{settings.ZETARIS_BASE_URL.rstrip('/')}/api/proxy/sql-editor/sqls/run-query",
                        json={"sql": sql, "limit": limit}, headers=headers)
        if r.status_code != 200:
            raise ZetarisError(f"Zetaris query failed: HTTP {r.status_code} {r.text[:200]}")
        body = r.json()
        names = [h["name"] if isinstance(h, dict) else str(h) for h in body.get("headers", [])]
        return [dict(zip(names, row)) for row in body.get("data", [])]
