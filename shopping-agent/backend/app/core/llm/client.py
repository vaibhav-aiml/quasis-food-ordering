"""LLM client abstraction.

``LLMClient`` is a structural ``Protocol`` — any object with a matching
``chat`` method satisfies it, no inheritance required. This is what lets
tests use a plain ``FakeLLMClient`` with zero mocking-library involvement,
and what would let a future non-Ollama backend (e.g. a hosted API) be
swapped in without touching anything that depends on this interface.
"""

from typing import Any, Protocol

from app.core.config import Settings
from app.core.llm.exceptions import LLMConnectionError


class LLMClient(Protocol):
    """The one method every LLM backend implementation must provide."""

    def chat(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Send a chat-style conversation and return the raw text reply.

        Args:
            messages: OpenAI/Ollama-style message list, each a dict with
                ``role`` (``system``/``user``/``assistant``) and ``content``.
            response_format: Optional JSON schema (e.g.
                ``SomeModel.model_json_schema()``) to constrain the model's
                output. ``None`` means unconstrained free text.

        Returns:
            The raw text of the model's reply. Callers are responsible for
            parsing/validating it — this layer only talks to the model.

        Raises:
            LLMConnectionError: if the backend could not be reached at all.
        """
        ...


class OllamaLLMClient:
    """``LLMClient`` implementation backed by a local Ollama server.

    Uses schema-constrained decoding (passing a JSON schema to Ollama's
    ``format`` parameter) rather than plain ``format="json"`` — per
    Ollama's own documentation this produces materially more reliable
    structured output, which matters here since downstream ranking
    correctness depends on well-formed intent/product data.
    """

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        """
        Args:
            settings: Used for ``ollama_base_url`` and ``ollama_model``.
            client: Optional pre-built ``ollama.Client``. Exposed purely so
                tests could construct an ``OllamaLLMClient`` against a fake
                underlying client if ever needed — in practice, tests
                should prefer a ``FakeLLMClient`` implementing the
                ``LLMClient`` protocol directly instead of reaching this
                deep.
        """
        self._model = settings.ollama_model
        self._client = client or self._build_default_client(settings)

    @staticmethod
    def _build_default_client(settings: Settings) -> Any:
        import ollama

        return ollama.Client(host=settings.ollama_base_url)

    def chat(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> str:
        try:
            response = self._client.chat(
                model=self._model,
                messages=messages,
                format=response_format,
            )
        except Exception as exc:
            # The `ollama` library's exception surface (connection errors,
            # ollama.ResponseError for API-level failures, etc.) isn't
            # narrowly typed here on purpose — see Phase 3 known
            # limitations. Everything is treated as "couldn't get a
            # response" until this has been exercised against a real
            # server and the specific exception types are confirmed.
            raise LLMConnectionError(
                f"Failed to reach Ollama at configured host for model "
                f"'{self._model}': {exc}"
            ) from exc

        if hasattr(response, "message") and hasattr(response.message, "content"):
            return response.message.content
        if isinstance(response, dict):
            msg = response.get("message", {})
            if isinstance(msg, dict):
                return msg.get("content", "")
            return getattr(msg, "content", "")
        return str(response)
