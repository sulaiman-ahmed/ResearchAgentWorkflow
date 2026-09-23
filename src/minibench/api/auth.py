"""Authentication helpers.

Derives reviewer/worker principals from validated server-side keys.
The caller never supplies a role — it is inferred from which key matches.
This is a local-demo boundary, not enterprise authentication.
"""

from __future__ import annotations

from enum import StrEnum

from fastapi import Header, HTTPException, status

from minibench.settings import settings


class Principal(StrEnum):
    reviewer = "reviewer"
    worker = "worker"


def _get_principal(api_key: str) -> Principal:
    if api_key and api_key == settings.reviewer_api_key:
        return Principal.reviewer
    if api_key and api_key == settings.worker_api_key:
        return Principal.worker
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def require_reviewer(x_api_key: str = Header(..., alias="X-Api-Key")) -> Principal:
    principal = _get_principal(x_api_key)
    if principal != Principal.reviewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reviewer key required")
    return principal


def require_any(x_api_key: str = Header(..., alias="X-Api-Key")) -> Principal:
    return _get_principal(x_api_key)
