"""Authenticated, read-only HTTP transport for dashboard application services."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from casita.bootstrap.application import NuestraCasitaApplication
from casita.domain import Household


COOKIE_NAME = "casita_session"


@dataclass(frozen=True, slots=True)
class DashboardApiConfiguration:
    """Validated Dashboard API configuration."""

    password: str
    session_secret: str
    host: str = "127.0.0.1"
    port: int = 8080
    session_ttl_seconds: int = 86400
    cookie_secure: bool = True
    allowed_origins: tuple[str, ...] = ()
    log_level: str = "info"


def load_dashboard_api_configuration() -> DashboardApiConfiguration:
    """Load API-only settings without changing CLI configuration behavior."""

    password = os.getenv("CASITA_API_PASSWORD", "")
    secret = os.getenv("CASITA_API_SESSION_SECRET", "")

    if len(password) < 12:
        raise RuntimeError("CASITA_API_PASSWORD must contain at least 12 characters.")
    if len(secret) < 32:
        raise RuntimeError(
            "CASITA_API_SESSION_SECRET must contain at least 32 characters."
        )

    try:
        port = int(os.getenv("CASITA_API_PORT", "8080"))
        ttl = int(os.getenv("CASITA_API_SESSION_TTL_SECONDS", "86400"))
    except ValueError as error:
        raise RuntimeError("Dashboard API port and session TTL must be integers.") from error

    if not 1 <= port <= 65535 or ttl <= 0:
        raise RuntimeError("Dashboard API port or session TTL is outside its valid range.")

    secure = os.getenv("CASITA_API_COOKIE_SECURE", "1").strip().casefold()
    if secure not in {"0", "1", "false", "true", "no", "yes"}:
        raise RuntimeError("CASITA_API_COOKIE_SECURE must be a boolean.")

    origins = tuple(
        item.strip()
        for item in os.getenv("CASITA_API_ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    )
    if "*" in origins:
        raise RuntimeError("Wildcard Dashboard API origins are not allowed.")

    return DashboardApiConfiguration(
        password=password,
        session_secret=secret,
        host=os.getenv("CASITA_API_HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=port,
        session_ttl_seconds=ttl,
        cookie_secure=secure in {"1", "true", "yes"},
        allowed_origins=origins,
        log_level=os.getenv("CASITA_API_LOG_LEVEL", "info").strip() or "info",
    )


class LoginRequest(BaseModel):
    """Password submitted by a same-origin browser login form."""

    password: str


def json_value(value: Any) -> Any:
    """Serialize backend-neutral immutable models with stable scalar formats."""

    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list, set, frozenset)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    return value


def create_dashboard_api(
    application: NuestraCasitaApplication,
    config: DashboardApiConfiguration,
) -> FastAPI:
    """Create one application-scoped FastAPI transport."""

    if application.configuration is None:
        raise RuntimeError("Dashboard API requires application configuration.")

    api = FastAPI(
        title="Nuestra Casita Dashboard API",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    if config.allowed_origins:
        api.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.allowed_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type"],
        )

    def sign(expiry: int) -> str:
        payload = str(expiry)
        signature = hmac.new(
            config.session_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return f"{payload}.{signature}"

    def authenticate(casita_session: str | None = Cookie(default=None)) -> None:
        if not casita_session or "." not in casita_session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        expiry_text, signature = casita_session.split(".", 1)
        try:
            expiry = int(expiry_text)
        except ValueError:
            expiry = 0
        expected = sign(expiry).split(".", 1)[1]
        if expiry < int(time.time()) or not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    def envelope(data: Any, failures=()) -> dict[str, Any]:
        safe_errors = [
            {
                "code": "integration_unavailable",
                "source": getattr(failure, "integration_key", None)
                or getattr(failure, "source", "integration"),
                "capability": (
                    failure.capability.value
                    if isinstance(failure.capability, Enum)
                    else str(failure.capability)
                ),
                "message": "Integration data could not be loaded.",
            }
            for failure in failures
        ]
        serialized = json_value(data)
        empty = serialized in ([], {}, None) or (
            isinstance(serialized, dict)
            and not any(serialized.values())
        )
        state = "degraded" if safe_errors else ("empty" if empty else "available")
        return {"version": "1", "state": state, "data": serialized, "errors": safe_errors}

    @api.get("/api/v1/health")
    def health():
        return {"status": "ok", "service": "nuestra-casita-dashboard-api"}

    @api.post("/api/v1/session", status_code=status.HTTP_204_NO_CONTENT)
    def login(request: LoginRequest, response: Response):
        if not hmac.compare_digest(request.password, config.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
        response.set_cookie(
            COOKIE_NAME,
            sign(int(time.time()) + config.session_ttl_seconds),
            max_age=config.session_ttl_seconds,
            httponly=True,
            secure=config.cookie_secure,
            samesite="strict",
            path="/api/v1",
        )

    @api.delete("/api/v1/session", status_code=status.HTTP_204_NO_CONTENT)
    def logout(response: Response, _: None = Depends(authenticate)):
        response.delete_cookie(COOKIE_NAME, path="/api/v1")

    services = application.services
    household_id = application.configuration.household_id

    def service_response(service):
        result = service.read(household_id)
        return envelope(result.records, result.failures)

    @api.get("/api/v1/dashboard", dependencies=[Depends(authenticate)])
    def dashboard():
        cfg = application.configuration
        household = Household(
            id=cfg.household_id,
            name=cfg.household_name,
            timezone=cfg.timezone,
        )
        snapshot = application.dashboard.build(household)
        return envelope(snapshot, snapshot.issues)

    endpoints = {
        "/api/v1/inventory": services.inventory,
        "/api/v1/shopping-lists": services.shopping,
        "/api/v1/recipes": services.recipes,
        "/api/v1/chores": services.chores,
        "/api/v1/meal-plan": services.meal_plan,
        "/api/v1/tasks": services.tasks,
    }

    def make_service_handler(service):
        def handler():
            return service_response(service)

        return handler

    for path, service in endpoints.items():
        api.add_api_route(
            path,
            make_service_handler(service),
            methods=["GET"],
            dependencies=[Depends(authenticate)],
        )

    return api
