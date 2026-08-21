"""Exception hierarchy for the LLM layer.

Every caller (agents, from Phase 4 onward) catches these instead of raw
``ollama`` exceptions or ``pydantic.ValidationError`` — this is the one
place that translates "the LLM backend misbehaved" into typed,
project-specific errors, so a future backend swap (e.g. away from Ollama)
doesn't leak library-specific exception types into agent code.
"""

from typing import Any


class LLMError(Exception):
    """Base class for all LLM-layer errors."""


class LLMConnectionError(LLMError):
    """Raised when the LLM backend (Ollama) could not be reached at all.

    Distinct from ``LLMValidationError`` because it means "the model never
    even responded" — callers may want to treat this as a hard failure
    rather than something retryable within the same request.
    """


class LLMValidationError(LLMError):
    """Raised when the model's output never validated against the target
    schema, even after retries.

    Carries the last raw response and validation error details so callers
    can log enough context to debug prompt quality issues later.
    """

    def __init__(
        self,
        message: str,
        *,
        raw_response: str | None,
        validation_errors: Any,
        attempts: int,
    ) -> None:
        super().__init__(message)
        self.raw_response = raw_response
        self.validation_errors = validation_errors
        self.attempts = attempts
