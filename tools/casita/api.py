"""Authenticated HTTP transport for dashboard application services."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from casita.bootstrap.application import NuestraCasitaApplication
from casita.domain import Household
from casita.integrations import (
    AddShoppingItem,
    CompleteChore,
    OperationConflict,
    OperationNotFound,
    RemoveShoppingItem,
    ShoppingItemStateChange,
)


COOKIE_NAME = "casita_session"
CSRF_COOKIE_NAME = "casita_csrf"


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


class AddShoppingItemRequest(BaseModel):
    """Bounded browser input for one shopping-list item."""

    product_id: str | None = Field(default=None, max_length=64)
    unit_id: str | None = Field(default=None, max_length=64)
    quantity: Decimal = Field(gt=0, le=Decimal("1000000"))
    note: str = Field(default="", max_length=500)


class ShoppingItemStateRequest(BaseModel):
    """Explicit requested purchased state."""

    purchased: bool


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
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
        )

    def sign(expiry: int) -> str:
        payload = str(expiry)
        signature = hmac.new(
            config.session_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return f"{payload}.{signature}"

    def sign_csrf(expiry: int, nonce: str) -> str:
        payload = f"{expiry}.{nonce}"
        signature = hmac.new(
            config.session_secret.encode(),
            f"csrf.{payload}".encode(),
            hashlib.sha256,
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

    def verify_csrf(
        casita_csrf: str | None = Cookie(default=None),
        x_csrf_token: str | None = Header(default=None),
    ) -> None:
        if not casita_csrf or not x_csrf_token or not hmac.compare_digest(
            casita_csrf, x_csrf_token
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request verification failed.",
            )
        parts = casita_csrf.split(".")
        if len(parts) != 3:
            raise HTTPException(status_code=403, detail="Request verification failed.")
        expiry_text, nonce, signature = parts
        try:
            expiry = int(expiry_text)
        except ValueError:
            expiry = 0
        expected = sign_csrf(expiry, nonce).rsplit(".", 1)[1]
        if expiry < int(time.time()) or not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=403, detail="Request verification failed.")

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
        expiry = int(time.time()) + config.session_ttl_seconds
        response.set_cookie(
            COOKIE_NAME,
            sign(expiry),
            max_age=config.session_ttl_seconds,
            httponly=True,
            secure=config.cookie_secure,
            samesite="strict",
            path="/api/v1",
        )
        response.set_cookie(
            CSRF_COOKIE_NAME,
            sign_csrf(expiry, secrets.token_urlsafe(24)),
            max_age=config.session_ttl_seconds,
            httponly=False,
            secure=config.cookie_secure,
            samesite="strict",
            path="/",
        )

    @api.delete("/api/v1/session", status_code=status.HTTP_204_NO_CONTENT)
    def logout(
        response: Response,
        _: None = Depends(authenticate),
        __: None = Depends(verify_csrf),
    ):
        response.delete_cookie(COOKIE_NAME, path="/api/v1")
        response.delete_cookie(CSRF_COOKIE_NAME, path="/")

    services = application.services
    household_id = application.configuration.household_id

    idempotency_lock = threading.Lock()
    idempotency_results: dict[str, tuple[str, Any] | None] = {}

    def mutation(
        operation: str,
        key: str | None,
        payload: Any,
        action,
    ) -> Any:
        if key is None or not 8 <= len(key) <= 128:
            raise HTTPException(
                status_code=400,
                detail="A valid Idempotency-Key header is required.",
            )
        fingerprint = hashlib.sha256(
            json.dumps(json_value(payload), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        token = f"{operation}:{key}"
        with idempotency_lock:
            prior = idempotency_results.get(token, "missing")
            if prior is None:
                raise HTTPException(status_code=409, detail="That request is already in progress.")
            if prior != "missing":
                prior_fingerprint, result = prior
                if prior_fingerprint != fingerprint:
                    raise HTTPException(status_code=409, detail="That request key was already used.")
                return result
            if len(idempotency_results) >= 512:
                idempotency_results.pop(next(iter(idempotency_results)))
            idempotency_results[token] = None
        try:
            result = action()
        except Exception as error:
            with idempotency_lock:
                idempotency_results.pop(token, None)
            if isinstance(error, OperationNotFound):
                raise HTTPException(status_code=404, detail=str(error)) from error
            if isinstance(error, OperationConflict):
                raise HTTPException(status_code=409, detail=str(error)) from error
            if isinstance(error, ValueError):
                raise HTTPException(status_code=400, detail=str(error)) from error
            if isinstance(error, TimeoutError):
                raise HTTPException(status_code=504, detail="The backend timed out.") from error
            raise HTTPException(status_code=502, detail="The backend operation failed.") from error
        with idempotency_lock:
            idempotency_results[token] = (fingerprint, result)
        return result

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

    write_dependencies = [Depends(authenticate), Depends(verify_csrf)]

    @api.get("/api/v1/shopping-products", dependencies=[Depends(authenticate)])
    def shopping_products(query: str, limit: int = 20):
        try:
            return envelope(services.shopping.search_products(query, limit=limit))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=502, detail="Product search failed.") from error

    @api.post(
        "/api/v1/shopping-lists/{shopping_list_id}/items",
        dependencies=write_dependencies,
    )
    def add_shopping_item(
        shopping_list_id: str,
        request: AddShoppingItemRequest,
        idempotency_key: str | None = Header(default=None),
    ):
        command = AddShoppingItem(
            household_id=household_id,
            shopping_list_id=shopping_list_id,
            product_id=request.product_id,
            unit_id=request.unit_id,
            quantity=request.quantity,
            note=request.note,
        )
        return mutation(
            "shopping-add",
            idempotency_key,
            command,
            lambda: envelope(
                (result := services.shopping.add_item(command)).records,
                result.failures,
            ),
        )

    @api.put(
        "/api/v1/shopping-lists/{shopping_list_id}/items/{item_id}",
        dependencies=write_dependencies,
    )
    def set_shopping_item_state(
        shopping_list_id: str,
        item_id: str,
        request: ShoppingItemStateRequest,
        idempotency_key: str | None = Header(default=None),
    ):
        command = ShoppingItemStateChange(
            household_id=household_id,
            shopping_list_id=shopping_list_id,
            item_id=item_id,
            purchased=request.purchased,
        )
        return mutation(
            "shopping-state",
            idempotency_key,
            command,
            lambda: envelope(
                (result := services.shopping.set_purchased(command)).records,
                result.failures,
            ),
        )

    @api.delete(
        "/api/v1/shopping-lists/{shopping_list_id}/items/{item_id}",
        dependencies=write_dependencies,
    )
    def remove_shopping_item(
        shopping_list_id: str,
        item_id: str,
        idempotency_key: str | None = Header(default=None),
    ):
        command = RemoveShoppingItem(household_id, shopping_list_id, item_id)
        return mutation(
            "shopping-remove",
            idempotency_key,
            command,
            lambda: envelope(
                (result := services.shopping.remove_item(command)).records,
                result.failures,
            ),
        )

    @api.post(
        "/api/v1/chores/{chore_id}/complete",
        dependencies=write_dependencies,
    )
    def complete_chore(
        chore_id: str,
        idempotency_key: str | None = Header(default=None),
    ):
        command = CompleteChore(household_id, chore_id)
        return mutation(
            "chore-complete",
            idempotency_key,
            command,
            lambda: envelope(
                (result := services.chores.complete(command)).records,
                result.failures,
            ),
        )

    return api
