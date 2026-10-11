"""API interna candidata. Histórico permanece deshabilitado."""

import asyncio
import json
import math
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .activities import CATALOG_VERSION, SELECTOR_VERSION, InvalidSelection, select_activities
from .pmum import CachedPmum, ModelUnavailable

API_VERSION = "analytics-api-v1-candidate"


def reply(payload, status=200):
    return JSONResponse(payload, status_code=status, headers={"Cache-Control": "no-store"})


class TransportGuard:
    """Autenticación y límites antes de leer/parsear el cuerpo."""
    def __init__(self, app, settings):
        self.app, self.settings = app, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = scope.get("headers", [])
        public_health = scope["method"] == "GET" and scope["path"] in {"/health", "/health/live"}
        auth = [value for key, value in headers if key == b"authorization"]
        expected = ("Bearer " + self.settings.token).encode("ascii")
        if not public_health and (len(auth) != 1 or not secrets.compare_digest(auth[0], expected)):
            return await reply({"error": "unauthorized"}, 401)(scope, receive, send)
        if scope["method"] in {"POST", "PUT", "PATCH"}:
            lengths = [v for k, v in headers if k == b"content-length"]
            transfer = [v for k, v in headers if k == b"transfer-encoding"]
            declared = None
            if lengths:
                if len(lengths) != 1 or len(lengths[0]) > 10 or not lengths[0].isdigit() or transfer:
                    return await reply({"error": "invalid_content_length"}, 400)(scope, receive, send)
                declared = int(lengths[0])
                if declared > self.settings.max_body_bytes:
                    return await reply({"error": "body_too_large"}, 413)(scope, receive, send)
            body = bytearray()
            async def collect():
                while True:
                    event = await receive()
                    if event["type"] == "http.disconnect":
                        return "disconnected"
                    if event["type"] != "http.request":
                        return "invalid_body"
                    chunk = event.get("body", b"")
                    if len(body) + len(chunk) > self.settings.max_body_bytes:
                        return "body_too_large"
                    body.extend(chunk)
                    if not event.get("more_body", False):
                        return None
            try:
                error = await asyncio.wait_for(collect(), self.settings.body_timeout_seconds)
            except asyncio.TimeoutError:
                return await reply({"error": "body_timeout"}, 408)(scope, receive, send)
            if error == "disconnected":
                return
            if error:
                return await reply({"error": error}, 413 if error == "body_too_large" else 400)(scope, receive, send)
            if declared is not None and declared != len(body):
                return await reply({"error": "incomplete_body"}, 400)(scope, receive, send)
            delivered = False
            original_receive = receive
            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await original_receive()
            receive = replay
        return await self.app(scope, receive, send)


def _strict_json(body):
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("JSON no finito")
        return result
    def constant(_):
        raise ValueError("JSON no finito")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Clave duplicada")
            result[key] = value
        return result
    return json.loads(body.decode("utf-8"), parse_constant=constant,
                      parse_float=finite_float, object_pairs_hook=pairs)


def create_app(settings):
    @asynccontextmanager
    async def lifespan(app):
        # No servir READY antes de completar la validación.
        app.state.pmum = CachedPmum(settings) if settings.pmum_enabled else None
        app.state.started = True
        try:
            yield
        finally:
            app.state.started = False
            app.state.pmum = None

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.started, app.state.pmum = False, None
    app.add_middleware(TransportGuard, settings=settings)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        names = {404: "not_found", 405: "method_not_allowed"}
        response = reply({"error": names.get(exc.status_code, "http_error")}, exc.status_code)
        if exc.status_code == 405 and exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        return reply({"error": "internal_error"}, 500)

    @app.get("/health/live")
    def live():
        return reply({"status": "up", "api_version": API_VERSION})

    @app.get("/health")
    def health():
        model = app.state.pmum
        pmum_ready = bool(model and model.ready)
        ready = (app.state.started and (settings.pmum_enabled or settings.activities_enabled)
                 and (not settings.pmum_enabled or pmum_ready))
        return reply({
            "status": "ready" if ready else "not_ready", "api_version": API_VERSION,
            "capabilities": {
                "pmum": {"state": "DISABLED" if not settings.pmum_enabled else "READY" if pmum_ready else "UNAVAILABLE",
                         "model_version": model.version if model else None},
                "activities": {"state": "READY" if settings.activities_enabled and app.state.started else "DISABLED" if not settings.activities_enabled else "UNAVAILABLE",
                               "catalog_version": CATALOG_VERSION, "selector_version": SELECTOR_VERSION, "catalog_status": "PROVISIONAL"},
                "historical": {"state": "DISABLED", "implemented": False},
            },
        }, 200 if ready else 503)

    @app.post("/experimental/pmum-estimate")
    async def estimate(request: Request):
        if not app.state.started or not settings.pmum_enabled:
            return reply({"error": "pmum_disabled"}, 503)
        parsed, error = await parse(request)
        if error is not None:
            return error
        from starlette.concurrency import run_in_threadpool
        try:
            return reply(await run_in_threadpool(app.state.pmum.estimate, parsed))
        except ModelUnavailable:
            return reply({"error": "model_unavailable"}, 503)

    @app.post("/v1/activities/select")
    async def activities(request: Request):
        if not app.state.started or not settings.activities_enabled:
            return reply({"error": "activities_disabled"}, 503)
        parsed, error = await parse(request)
        if error is not None:
            return error
        try:
            return reply(select_activities(parsed))
        except InvalidSelection:
            return reply({"error": "invalid_selection_request"}, 400)

    @app.post("/v1/historical/evaluate")
    def historical():
        return reply({"error": "historical_not_implemented"}, 503)

    return app


async def parse(request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        return None, reply({"error": "json_content_type_required"}, 415)
    try:
        return _strict_json(await request.body()), None
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None, reply({"error": "invalid_json"}, 400)
