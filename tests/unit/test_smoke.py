"""Smoke tests — verify the package imports and basic config loads."""

from minibench.main import app
from minibench.settings import settings


def test_app_exists() -> None:
    assert app.title == "minibench"


def test_settings_model_mode_default() -> None:
    # CI sets MODEL_MODE=fake via environment; default is also fake
    assert settings.model_mode in ("fake", "live")


def test_health_route_registered() -> None:
    paths = [r.path for r in app.routes if hasattr(r, "path")]  # type: ignore[union-attr]
    assert "/health" in paths
    assert "/ready" in paths
