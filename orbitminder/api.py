"""Private, read-only FastAPI gateway for Inboxtend task summaries.

Run behind HTTPS/reverse proxy. All secrets are server-side. This gateway does
not write tasks, trigger agents, or invent an owner from client parameters.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from pydantic import ValidationError

from .inboxtend_contract import InboxtendTaskPage

app = FastAPI(
    title="OrbitMinder private task API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def _config(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise HTTPException(status_code=503, detail="Integration not configured")
    return value


def _authorized(authorization: str | None = Header(default=None)) -> None:
    """Use separately configured gateway and upstream credentials."""
    import hmac

    expected = _config("ORBITMINDER_API_TOKEN")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Bearer"})
    if not hmac.compare_digest(authorization.removeprefix("Bearer "), expected):
        raise HTTPException(status_code=401, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Bearer"})


@app.get("/api/v1/inboxtend/tasks", response_model=InboxtendTaskPage,
         dependencies=[Depends(_authorized)])
async def read_tasks(
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = Query(default=None, min_length=1, max_length=2048),
) -> InboxtendTaskPage:
    """Proxy an owner-scoped upstream read credential; never expose it to browsers."""
    response.headers["Cache-Control"] = "private, no-store"
    base_url = _config("INBOXTEND_READONLY_BASE_URL").rstrip("/")
    url = urlsplit(base_url)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise HTTPException(status_code=503, detail="Invalid integration configuration")
    upstream_token = _config("INBOXTEND_READONLY_TOKEN")
    params: dict[str, str | int] = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=False) as client:
            result = await client.get(
                base_url + "/integration/v1/tasks",
                params=params,
                headers={"Authorization": f"Bearer {upstream_token}",
                         "Accept": "application/json"},
            )
        if result.status_code in (401, 403):
            raise HTTPException(status_code=502, detail="Upstream authorization failed")
        if result.status_code != 200:
            raise HTTPException(status_code=502, detail="Upstream task feed unavailable")
        return InboxtendTaskPage.model_validate(result.json())
    except (httpx.RequestError, ValueError, ValidationError):
        raise HTTPException(status_code=502, detail="Upstream task feed invalid or unavailable")
