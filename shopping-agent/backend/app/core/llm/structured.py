"""Structured, validated LLM output generation.

This is the only way the rest of the application should ever ask the LLM
for data — never raw ``client.chat()`` calls scattered around agent code.
Centralizing it here means the retry/validation policy (and the exception
types callers need to handle) is defined exactly once.
"""

import json
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.llm.client import LLMClient
from app.core.llm.exceptions import LLMValidationError
from app.core.llm.prompts import PromptManager

T = TypeVar("T", bound=BaseModel)

_logger = logging.getLogger("app.llm.structured")


class StructuredLLMService:
    """Generates LLM output validated against a Pydantic model.

    Flow per call:

    1. Render the named prompt template, embedding the target model's JSON
       schema as ``$schema`` (available to any template that wants it).
    2. Call the LLM with that schema also passed as Ollama's native
       ``format`` constraint — belt-and-suspenders: schema-constrained
       decoding does most of the work, the in-prompt schema text helps
       smaller/less-compliant models and keeps behavior sane if this is
       ever pointed at a backend without native format constraints.
    3. Parse the reply as JSON, then validate against the Pydantic model.
    4. On JSON-parse or validation failure, append the bad reply plus a
       corrective message to the conversation and retry, up to
       ``max_retries`` additional attempts.
    5. If still invalid after all attempts, raise ``LLMValidationError``
       with the last raw response and error details attached.
    """

    def __init__(
        self,
        client: LLMClient,
        prompt_manager: PromptManager,
        *,
        max_retries: int = 2,
    ) -> None:
        self._client = client
        self._prompts = prompt_manager
        self._max_retries = max_retries

    def generate(
        self,
        *,
        template_name: str,
        response_model: type[T],
        variables: dict[str, str],
        system_prompt: str | None = None,
    ) -> T:
        """Generate and validate structured output.

        Args:
            template_name: Name of a ``.txt`` file under
                ``app/core/llm/prompt_templates/`` (without extension).
            response_model: The Pydantic model the output must validate
                against.
            variables: Values substituted into the template. The template's
                own ``$schema`` placeholder, if present, is filled in
                automatically — don't pass ``schema`` yourself.
            system_prompt: Optional system-role message prepended to the
                conversation.

        Returns:
            A validated instance of ``response_model``.

        Raises:
            LLMConnectionError: if the LLM backend is unreachable — not
                caught here, propagates straight to the caller.
            LLMValidationError: if valid output wasn't produced within
                ``max_retries`` retries.
        """

        schema = response_model.model_json_schema()
        user_prompt = self._prompts.render(
            template_name, schema=json.dumps(schema), **variables
        )

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        last_raw: str | None = None
        last_error: str = ""

        for attempt in range(1, self._max_retries + 2):
            raw = self._client.chat(messages=messages, response_format=schema)
            last_raw = raw

            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                last_error = f"Response was not valid JSON: {exc}"
                _logger.warning(
                    "llm_output_not_json",
                    extra={"attempt": attempt, "template": template_name},
                )
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"That was not valid JSON ({exc}). Respond again "
                            "with ONLY valid JSON matching the schema, no "
                            "other text."
                        ),
                    }
                )
                continue

            try:
                return response_model.model_validate(data)
            except ValidationError as exc:
                last_error = str(exc)
                _logger.warning(
                    "llm_output_failed_validation",
                    extra={"attempt": attempt, "template": template_name},
                )
                messages.append({"role": "assistant", "content": raw})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"That JSON did not match the required schema. "
                            f"Errors: {exc}. Respond again with ONLY "
                            "corrected valid JSON."
                        ),
                    }
                )
                continue

        raise LLMValidationError(
            f"No valid '{response_model.__name__}' output after "
            f"{self._max_retries + 1} attempts",
            raw_response=last_raw,
            validation_errors=last_error,
            attempts=self._max_retries + 1,
        )
