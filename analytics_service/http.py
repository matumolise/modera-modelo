"""API interna candidata; capacidades habilitadas por configuración explícita."""

import asyncio
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .activities import CATALOG_VERSION, SELECTOR_VERSION, InvalidSelection, select_activities
from .pmum import CachedPmum, ModelUnavailable
from .historical_api import (HistoricalRuntime, HistoricalConflict, HistoricalUnavailable,
                             InvalidHistoricalRequest, parse_historical_request)
from .historical_config import HISTORICAL_API_VERSION
from .condition_mapping import MAPPING_VERSION, resolve_considerations
from .json_codec import strict_json as _strict_json
from .adult_messages import AdultMessageService, MessageConflict, MessageUnavailable, VERSION as MESSAGES_VERSION
from .child_offer_api import (
    ChildOfferRuntime, CoordinatorConflict, CoordinatorUnavailable,
    COORDINATOR_API_VERSION, POLICY as CHILD_POLICY, parse_evaluation, parse_event,
)

API_VERSION = "analytics-api-v3-integration-candidate"


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


def create_app(settings):
    @asynccontextmanager
    async def lifespan(app):
        # No servir READY antes de completar la validación.
        try:
            app.state.pmum = CachedPmum(settings) if settings.pmum_enabled else None
            app.state.historical = HistoricalRuntime(settings) if settings.historical_enabled else None
            app.state.adult_messages = AdultMessageService(settings.adult_messages_repository_path) if settings.adult_messages_enabled else None
            app.state.child_offers = ChildOfferRuntime(settings.child_offers_repository_path) if settings.child_offers_enabled else None
            app.state.started = True
            yield
        finally:
            app.state.started = False
            if app.state.historical is not None:
                app.state.historical.close()
            app.state.historical = None
            app.state.pmum = None
            app.state.adult_messages = None
            app.state.child_offers = None

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.started, app.state.pmum = False, None
    app.state.historical = None
    app.state.adult_messages = None
    app.state.child_offers = None
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
        historical = app.state.historical
        historical_ready = bool(historical and historical.check_ready())
        messages_ready = bool(app.state.adult_messages and app.state.adult_messages.check_ready())
        child_ready = bool(app.state.child_offers and app.state.child_offers.check_ready())
        ready = (app.state.started and (settings.pmum_enabled or settings.activities_enabled or settings.historical_enabled or settings.adult_messages_enabled or settings.child_offers_enabled)
                 and (not settings.pmum_enabled or pmum_ready)
                 and (not settings.adult_messages_enabled or messages_ready)
                 and (not settings.child_offers_enabled or child_ready)
                 and (not settings.historical_enabled or historical_ready))
        return reply({
            "status": "ready" if ready else "not_ready", "api_version": API_VERSION,
            "capabilities": {
                **({"child_offers": {"state": "READY" if child_ready and app.state.started else "UNAVAILABLE",
                                     "api_version": COORDINATOR_API_VERSION,
                                     "policy_version": CHILD_POLICY["version"],
                                     "catalog_status": "PROVISIONAL", "scope": "internal_integration_candidate"}}
                   if settings.child_offers_enabled else {}),
                **({"adult_messages": {"state": "READY" if messages_ready and app.state.started else "UNAVAILABLE",
                                       "version": MESSAGES_VERSION, "scope": "internal_candidate_not_family_validated"}}
                   if settings.adult_messages_enabled else {}),
                "pmum": {"state": "DISABLED" if not settings.pmum_enabled else "READY" if pmum_ready else "UNAVAILABLE",
                         "model_version": model.version if model else None},
                "activities": {"state": "READY" if settings.activities_enabled and app.state.started else "DISABLED" if not settings.activities_enabled else "UNAVAILABLE",
                               "catalog_version": CATALOG_VERSION, "selector_version": SELECTOR_VERSION,
                               "considerations_mapping_version": MAPPING_VERSION, "catalog_status": "PROVISIONAL"},
                "historical": {
                    "state": "DISABLED" if not settings.historical_enabled else "READY" if historical_ready else "UNAVAILABLE",
                    "implemented": True, "historical_api_version": HISTORICAL_API_VERSION,
                    "configuration_id": historical.profile.configuration_id if historical else None,
                    "configuration_fingerprint": historical.profile.fingerprint if historical else None,
                    "representation_spec_id": "daily_use_duration_minutes_v2",
                    "scope": "internal_technical_candidate",
                },
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

    @app.post("/v1/activities/eligibility")
    async def eligibility(request: Request):
        if not app.state.started or not settings.activities_enabled:
            return reply({"error": "activities_disabled"}, 503)
        parsed, error = await parse(request)
        if error is not None:
            return error
        try:
            return reply(resolve_considerations(parsed))
        except InvalidSelection:
            return reply({"error": "invalid_considerations_request"}, 400)

    @app.post("/v1/historical/evaluate")
    async def historical(request: Request):
        if not app.state.started or not settings.historical_enabled:
            return reply({"error": "historical_disabled"}, 503)
        parsed, error = await parse(request)
        if error is not None:
            return error
        try:
            request_id, current = parse_historical_request(parsed)
        except InvalidHistoricalRequest:
            return reply({"error": "invalid_historical_request"}, 400)
        from starlette.concurrency import run_in_threadpool
        try:
            return reply(await run_in_threadpool(app.state.historical.evaluate, request_id, current))
        except HistoricalConflict as exc:
            return reply({"error": str(exc)}, 409)
        except HistoricalUnavailable:
            return reply({"error": "historical_unavailable"}, 503)

    @app.post("/v1/adult-messages/evaluate")
    async def adult_messages(request: Request):
        if not app.state.started or app.state.adult_messages is None:
            return reply({"error": "adult_messages_disabled"}, 503)
        parsed, error = await parse(request)
        if error is not None:
            return error
        from starlette.concurrency import run_in_threadpool
        try:
            return reply(await run_in_threadpool(app.state.adult_messages.evaluate, parsed))
        except MessageConflict as exc:
            return reply({"error": str(exc)}, 409)
        except MessageUnavailable:
            return reply({"error": "adult_messages_unavailable"}, 503)
        except (ValueError, TypeError, OverflowError):
            return reply({"error": "invalid_adult_message_request"}, 400)

    @app.get("/v1/adult-messages/profiles/{profile_id}/history")
    async def adult_message_history(profile_id: str):
        if not app.state.started or app.state.adult_messages is None:
            return reply({"error": "adult_messages_disabled"}, 503)
        from starlette.concurrency import run_in_threadpool
        try:
            return reply({"versions": await run_in_threadpool(app.state.adult_messages.history, profile_id)})
        except ValueError:
            return reply({"error": "invalid_profile_id"}, 400)
        except MessageUnavailable:
            return reply({"error": "adult_messages_unavailable"}, 503)

    @app.post("/v1/child-offers/evaluate")
    async def child_offer_evaluation(request: Request):
        if not app.state.started or app.state.child_offers is None:
            return reply({"error": "child_offers_disabled"}, 503)
        parsed, error = await parse(request)
        if error is not None:
            return error
        from starlette.concurrency import run_in_threadpool
        try:
            request_id, evidence = parse_evaluation(parsed)
            return reply(await run_in_threadpool(app.state.child_offers.evaluate, request_id, evidence))
        except CoordinatorConflict:
            return reply({"error": "child_offer_conflict"}, 409)
        except CoordinatorUnavailable:
            return reply({"error": "child_offers_unavailable"}, 503)
        except (ValueError, TypeError, OverflowError):
            return reply({"error": "invalid_child_offer_request"}, 400)

    @app.post("/v1/child-offers/events")
    async def child_offer_event(request: Request):
        if not app.state.started or app.state.child_offers is None:
            return reply({"error": "child_offers_disabled"}, 503)
        parsed, error = await parse(request)
        if error is not None:
            return error
        from starlette.concurrency import run_in_threadpool
        try:
            request_id, payload = parse_event(parsed)
            return reply(await run_in_threadpool(app.state.child_offers.record_event, request_id, payload))
        except CoordinatorConflict:
            return reply({"error": "child_offer_conflict"}, 409)
        except CoordinatorUnavailable:
            return reply({"error": "child_offers_unavailable"}, 503)
        except (ValueError, TypeError, OverflowError):
            return reply({"error": "invalid_child_offer_event"}, 400)

    @app.get("/v1/child-offers/profiles/{profile_id}/history")
    async def child_offer_history(profile_id: str):
        if not app.state.started or app.state.child_offers is None:
            return reply({"error": "child_offers_disabled"}, 503)
        from starlette.concurrency import run_in_threadpool
        try:
            return reply(await run_in_threadpool(app.state.child_offers.history, profile_id))
        except CoordinatorUnavailable:
            return reply({"error": "child_offers_unavailable"}, 503)
        except ValueError:
            return reply({"error": "invalid_profile_id"}, 400)

    return app


async def parse(request):
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        return None, reply({"error": "json_content_type_required"}, 415)
    try:
        return _strict_json(await request.body()), None
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None, reply({"error": "invalid_json"}, 400)
