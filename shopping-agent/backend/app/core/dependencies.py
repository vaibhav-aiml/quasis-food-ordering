"""Dependency-injection seams for FastAPI's native ``Depends`` system.

This module is the entire "DI container" for the project (see Phase 2
design notes for why a third-party DI framework was rejected). Every
cross-cutting resource (settings, loggers, and — from later phases — the
LLM client, the LangGraph app, adapters) gets a factory function here and
is injected into routes/services via ``Depends(...)``, never imported as a
module-level singleton at the call site.

This is what keeps every module independently testable (rule #14): tests
call ``app.dependency_overrides[get_settings] = lambda: Settings(...)``
instead of monkeypatching globals.
"""

import logging
from functools import lru_cache

from app.adapters.base import StoreAdapter
from app.adapters.blinkit.adapter import BlinkitAdapter
from app.adapters.blinkit.appium_adapter import BlinkitAppiumAdapter
from app.adapters.instamart.adapter import InstamartAdapter
from app.adapters.instamart.appium_adapter import InstamartAppiumAdapter
from app.adapters.zepto.adapter import ZeptoAdapter
from app.adapters.zepto.appium_adapter import ZeptoAppiumAdapter
from app.agents.intent_agent import IntentUnderstandingAgent
from app.agents.recommendation_agent import RecommendationGenerator
from app.automation.driver_manager import DriverManager
from app.core.config import Settings, get_settings as _get_settings
from app.core.llm.client import LLMClient, OllamaLLMClient
from app.core.llm.prompts import PromptManager
from app.core.llm.structured import StructuredLLMService
from app.core.logging import get_logger as _get_logger
from app.graph.workflow import build_graph

# Re-exported so `from app.core.dependencies import get_settings` is the
# single import call sites need — they don't need to know it actually
# lives in `config.py`.
get_settings = _get_settings


@lru_cache
def get_app_logger() -> logging.Logger:
    """Dependency that provides the application's default logger.

    Cached so every caller within a process shares the same ``Logger``
    instance (stdlib loggers are already effectively singletons per name,
    but caching here keeps the pattern consistent with ``get_settings``).
    """

    return _get_logger("app")


@lru_cache
def get_llm_client() -> LLMClient:
    """Dependency providing the process-wide LLM client.

    Returns the ``OllamaLLMClient`` implementation today. Because callers
    depend on the ``LLMClient`` protocol (not this concrete class), a
    future backend swap only changes this one factory function.
    """

    return OllamaLLMClient(get_settings())


@lru_cache
def get_prompt_manager() -> PromptManager:
    """Dependency providing the process-wide prompt template manager."""

    return PromptManager()


@lru_cache
def get_structured_llm_service() -> StructuredLLMService:
    """Dependency providing the structured-output generation service.

    This is what agent code (Phase 4 onward) should actually depend on —
    not ``get_llm_client()`` directly — since it's the layer that adds
    schema validation and retry behavior on top of the raw client.
    """

    return StructuredLLMService(get_llm_client(), get_prompt_manager())


@lru_cache
def get_intent_agent() -> IntentUnderstandingAgent:
    """Dependency providing the Intent Understanding Agent.

    Depends on ``get_structured_llm_service()`` — not the raw LLM client —
    since the agent has no business handling retries/validation itself;
    that's already the structured service's job.
    """

    return IntentUnderstandingAgent(get_structured_llm_service())


@lru_cache
def get_recommendation_generator() -> RecommendationGenerator:
    """Dependency providing the Recommendation Generator.

    Same rationale as ``get_intent_agent()`` — depends on the structured
    service, not the raw LLM client, since retry/validation is already
    handled there.
    """

    return RecommendationGenerator(get_structured_llm_service())


@lru_cache
def get_shopping_graph(settings: Settings | None = None):
    """Dependency providing the compiled LangGraph shopping workflow.

    ``@lru_cache`` here is load-bearing, not just an optimization: the
    graph is compiled with ``checkpointer=InMemorySaver()``
    (``build_graph``), and that in-memory store is where every
    ``thread_id``'s state actually lives. Without caching, each call
    would build a *new* graph with a *brand-new, empty* ``InMemorySaver``
    — so a thread created by ``POST /v1/requests`` would already be gone
    by the time ``GET /v1/requests/{thread_id}`` (a separate request,
    separate ``Depends`` resolution) asked for it. One process-wide graph
    instance is required for the FastAPI integration (Phase 16) to have
    any state to drive at all.

    Uses Phase 7's mock adapters by default (deterministic, no real
    device needed) — swaps to real Appium-backed adapters when configured
    in settings (e.g. STORE_MODE=real or BLINKIT_STORE_MODE=real).
    """

    s = settings or get_settings()
    return build_graph(
        get_intent_agent(),
        list(get_all_store_adapters(s)),
        get_recommendation_generator(),
    )


def get_shopping_graph_dependency():
    """FastAPI-route-callable wrapper around ``get_shopping_graph()``.

    ``get_shopping_graph`` takes an optional ``settings: Settings | None``
    positional/keyword argument with no ``Depends(...)`` default. Passed
    directly to a route's ``Depends(get_shopping_graph)``, FastAPI would
    introspect that parameter too and — finding no ``Depends`` marker —
    treat it as an incoming *query parameter* of type ``Settings``,
    which is neither intended nor parseable from a query string. This
    zero-parameter wrapper is what endpoint modules should actually put
    behind ``Depends(...)``; it always resolves to the one process-wide
    graph built from the cached global ``Settings`` (Requirement:
    default API behavior stays mock/offline unless ``STORE_MODE``/
    ``*_STORE_MODE`` env vars say otherwise — see ``config.py``).
    """

    return get_shopping_graph()


def create_driver_manager(settings: Settings | None = None) -> DriverManager:
    """Factory (deliberately NOT ``@lru_cache``'d) for a fresh
    ``DriverManager``.

    Unlike ``Settings`` or the logger, there is no single correct
    process-wide ``DriverManager`` instance — it wraps one stateful
    Appium session, and each Store Adapter (Phase 7+) needs its own.
    Callers get a new, unstarted manager every call.
    """

    return DriverManager(settings or get_settings())


@lru_cache
def get_zepto_adapter() -> ZeptoAdapter:
    return ZeptoAdapter()


@lru_cache
def get_blinkit_adapter() -> BlinkitAdapter:
    return BlinkitAdapter()


@lru_cache
def get_instamart_adapter() -> InstamartAdapter:
    return InstamartAdapter()


def get_all_store_adapters(settings: Settings | None = None) -> tuple[StoreAdapter, ...]:
    """All supported store adapters, selected dynamically based on configuration.

    By default, returns mock adapters for all stores (deterministic, fast,
    no real device needed). When real mode is enabled for a store (e.g.,
    BLINKIT_STORE_MODE=real), instantiates its real Appium adapter.
    """

    s = settings or get_settings()
    blinkit: StoreAdapter = (
        create_blinkit_appium_adapter(s)
        if s.is_real_store("blinkit")
        else get_blinkit_adapter()
    )
    zepto: StoreAdapter = (
        create_zepto_appium_adapter(s)
        if s.is_real_store("zepto")
        else get_zepto_adapter()
    )
    instamart: StoreAdapter = (
        create_instamart_appium_adapter(s)
        if s.is_real_store("instamart")
        else get_instamart_adapter()
    )
    return (zepto, blinkit, instamart)


def create_zepto_appium_adapter(
    settings: Settings | None = None, driver_manager: DriverManager | None = None
) -> ZeptoAppiumAdapter:
    """Factory for a real, Appium-backed Zepto adapter.

    Deliberately NOT ``@lru_cache``'d — same reasoning as
    ``create_driver_manager``: this wraps a stateful Appium session (via
    its own internal ``DriverManager`` if one isn't injected), and there
    is no single correct process-wide instance.

    Reminder: ``app/adapters/zepto/locators.py`` currently holds
    unverified placeholder locator values — see Phase 8 docs before
    expecting this to work against the real app.
    """

    return ZeptoAppiumAdapter(settings or get_settings(), driver_manager)


def create_blinkit_appium_adapter(
    settings: Settings | None = None, driver_manager: DriverManager | None = None
) -> BlinkitAppiumAdapter:
    """Factory for a real, Appium-backed Blinkit adapter. See
    ``create_zepto_appium_adapter`` for the caching rationale.
    """

    return BlinkitAppiumAdapter(settings or get_settings(), driver_manager)


def create_instamart_appium_adapter(
    settings: Settings | None = None, driver_manager: DriverManager | None = None
) -> InstamartAppiumAdapter:
    """Factory for a real, Appium-backed Instamart adapter. See
    ``create_zepto_appium_adapter`` for the caching rationale.
    """

    return InstamartAppiumAdapter(settings or get_settings(), driver_manager)


__all__ = [
    "get_settings",
    "Settings",
    "get_app_logger",
    "get_llm_client",
    "get_prompt_manager",
    "get_structured_llm_service",
    "get_intent_agent",
    "get_recommendation_generator",
    "get_shopping_graph",
    "get_shopping_graph_dependency",
    "create_driver_manager",
    "get_zepto_adapter",
    "get_blinkit_adapter",
    "get_instamart_adapter",
    "get_all_store_adapters",
    "create_zepto_appium_adapter",
    "create_blinkit_appium_adapter",
    "create_instamart_appium_adapter",
]
