"""Tests for app.core.llm.structured.StructuredLLMService.

Uses a hand-written ``FakeLLMClient`` that satisfies the ``LLMClient``
protocol structurally — no mocking library, no real Ollama server. This is
exactly the payoff of defining ``LLMClient`` as a ``Protocol`` in Phase 3's
design.
"""

from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from app.core.llm.exceptions import LLMValidationError
from app.core.llm.prompts import PromptManager
from app.core.llm.structured import StructuredLLMService


class _PingResponse(BaseModel):
    """Minimal model used only to exercise the structured-output pipeline."""

    reply: str
    confidence: float


class FakeLLMClient:
    """Returns a pre-programmed sequence of raw responses, one per call.

    Lets tests script exactly how the "model" misbehaves across retries
    without any network access.
    """

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def chat(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self.calls.append({"messages": messages, "response_format": response_format})
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of scripted responses")
        return self._responses.pop(0)


@pytest.fixture
def prompt_manager(tmp_path: Path) -> PromptManager:
    (tmp_path / "example_ping.txt").write_text(
        "Schema: $schema\nMessage: $user_message", encoding="utf-8"
    )
    return PromptManager(templates_dir=tmp_path)


def test_generate_succeeds_on_first_valid_response(prompt_manager: PromptManager) -> None:
    client = FakeLLMClient(['{"reply": "hi", "confidence": 0.9}'])
    service = StructuredLLMService(client, prompt_manager)

    result = service.generate(
        template_name="example_ping",
        response_model=_PingResponse,
        variables={"user_message": "hello"},
    )

    assert result == _PingResponse(reply="hi", confidence=0.9)
    assert len(client.calls) == 1


def test_generate_retries_after_invalid_json_then_succeeds(
    prompt_manager: PromptManager,
) -> None:
    client = FakeLLMClient(
        [
            "not json at all",
            '{"reply": "recovered", "confidence": 0.5}',
        ]
    )
    service = StructuredLLMService(client, prompt_manager, max_retries=2)

    result = service.generate(
        template_name="example_ping",
        response_model=_PingResponse,
        variables={"user_message": "hello"},
    )

    assert result.reply == "recovered"
    assert len(client.calls) == 2
    # The corrective retry should include the bad output + a follow-up nudge.
    second_call_messages = client.calls[1]["messages"]
    assert second_call_messages[-2]["role"] == "assistant"
    assert second_call_messages[-1]["role"] == "user"


def test_generate_retries_after_schema_validation_failure(
    prompt_manager: PromptManager,
) -> None:
    client = FakeLLMClient(
        [
            '{"reply": "missing confidence field"}',  # valid JSON, invalid schema
            '{"reply": "fixed", "confidence": 1.0}',
        ]
    )
    service = StructuredLLMService(client, prompt_manager, max_retries=2)

    result = service.generate(
        template_name="example_ping",
        response_model=_PingResponse,
        variables={"user_message": "hello"},
    )

    assert result.reply == "fixed"
    assert len(client.calls) == 2


def test_generate_raises_after_exhausting_retries(prompt_manager: PromptManager) -> None:
    client = FakeLLMClient(
        [
            "not json",
            "still not json",
            "nope",
        ]
    )
    service = StructuredLLMService(client, prompt_manager, max_retries=2)

    with pytest.raises(LLMValidationError) as exc_info:
        service.generate(
            template_name="example_ping",
            response_model=_PingResponse,
            variables={"user_message": "hello"},
        )

    assert exc_info.value.attempts == 3
    assert exc_info.value.raw_response == "nope"
    assert len(client.calls) == 3


def test_generate_passes_schema_as_response_format(prompt_manager: PromptManager) -> None:
    client = FakeLLMClient(['{"reply": "hi", "confidence": 0.9}'])
    service = StructuredLLMService(client, prompt_manager)

    service.generate(
        template_name="example_ping",
        response_model=_PingResponse,
        variables={"user_message": "hello"},
    )

    assert client.calls[0]["response_format"] == _PingResponse.model_json_schema()
