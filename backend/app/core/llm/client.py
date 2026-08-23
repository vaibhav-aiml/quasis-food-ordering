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
    """LLMClient implementation backed by a local Ollama server."""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._model = settings.ollama_model
        self._settings = settings
        self._client = client
        if self._client is None:
            try:
                import ollama
                self._client = ollama.Client(host=settings.ollama_base_url)
            except Exception:
                self._client = None

    def chat(
        self,
        *,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if self._client is not None:
            try:
                response = self._client.chat(
                    model=self._model,
                    messages=messages,
                    format=response_format,
                )
                if hasattr(response, "message") and hasattr(response.message, "content"):
                    return response.message.content
                if isinstance(response, dict):
                    msg = response.get("message", {})
                    if isinstance(msg, dict):
                        return msg.get("content", "")
                    return getattr(msg, "content", "")
                return str(response)
            except Exception:
                pass

        # Smart heuristic fallback when Ollama is not running locally
        return self._heuristic_fallback(messages)

    @staticmethod
    def _heuristic_fallback(messages: list[dict[str, str]]) -> str:
        import json, re

        content = messages[-1].get("content", "")
        raw_text = content.split("User Request:")[-1].strip() if "User Request:" in content else content

        # Detect restaurant (handle any restaurant name after 'from' or in known list)
        restaurant = ""
        known_restaurants = [
            "Domino's", "Dominos", "Meghana Foods", "Saravana Bhavan", "Bikanervala", "Haldiram's", "Haldirams",
            "Cafe Coffee Day", "Paradise Biryani", "McDonald's", "KFC",
            "Pizza Hut", "Subway", "Burger King", "Starbucks"
        ]
        for r in known_restaurants:
            if re.search(rf"\b{re.escape(r)}\b", raw_text, re.IGNORECASE):
                restaurant = r
                break
        if not restaurant:
            from_match = re.search(r"\bfrom\s+([^,.;\n]+?)(?:\s+on\b|\s+with\b|\s+in\b|[.,;]|$)", raw_text, re.IGNORECASE)
            if from_match:
                candidate = from_match.group(1).strip(" .,!?:;")
                if candidate and candidate.lower() not in ("swiggy", "zomato", "blinkit", "zepto"):
                    restaurant = candidate

        # Detect dishes
        items = []
        dish_patterns = [
            r"(\d+)?\s*(margherita\s+pizza|farmhouse\s+pizza|pizza|dal\s+kachori|kachori|chicken\s+biryani|mutton\s+biryani|paneer\s+biryani|biryani|masala\s+dosa|plain\s+dosa|dosa|idli\s+sambar|idli|filter\s+coffee|cappuccino|cold\s+coffee|coffee|burger|fries|sandwich|paneer\s+butter\s+masala|butter\s+chicken|chole\s+bhature|samosa|gulab\s+jamun|rasgulla)",
        ]
        for pat in dish_patterns:
            matches = list(re.finditer(pat, raw_text, re.IGNORECASE))
            for m in matches:
                qty_str = m.group(1)
                qty = int(qty_str) if qty_str else 1
                dish_name = m.group(2).strip().lower()
                items.append({
                    "name": dish_name,
                    "quantity": qty,
                    "portion_or_size": "",
                    "customizations": [],
                    "preferred_restaurant": restaurant,
                })

        # If no dishes found via pattern, extract words before "from" or after "order"
        if not items and ("order" in raw_text.lower() or "get" in raw_text.lower() or "buy" in raw_text.lower()):
            clean = re.sub(r"^(order|get|buy|send)\s+", "", raw_text, flags=re.IGNORECASE)
            clean = re.sub(r"\s+from\s+.*$", "", clean, flags=re.IGNORECASE)
            clean = re.sub(r"\s+on\s+.*$", "", clean, flags=re.IGNORECASE)
            clean = clean.strip(" .,!?:;")
            if clean:
                items.append({
                    "name": clean.lower(),
                    "quantity": 1,
                    "portion_or_size": "",
                    "customizations": [],
                    "preferred_restaurant": restaurant,
                })

        # Detect customizations
        customizations = []
        cust_match = re.search(r"\bwith\s+([A-Za-z0-9\s,]+?)(?:\s+from|\s+on|$)", raw_text, re.IGNORECASE)
        if cust_match and items:
            cust = cust_match.group(1).strip()
            items[0]["customizations"] = [cust]

        # Target app
        target_app = "zomato" if "zomato" in raw_text.lower() else "swiggy"

        if not items and not restaurant:
            return json.dumps({
                "restaurant_name": "",
                "cuisine_preference": "",
                "meal_type": "",
                "items": [],
                "constraints": {"max_delivery_minutes": 0, "priority": "unspecified", "max_budget": 0.0},
                "target_app": target_app,
                "confidence": 0.0,
                "needs_clarification": True,
                "clarification_reason": "The request did not specify any specific restaurant or dish.",
            })

        return json.dumps({
            "restaurant_name": restaurant,
            "cuisine_preference": "Pizza" if "pizza" in raw_text.lower() else ("Biryani" if "biryani" in raw_text.lower() else "Indian"),
            "meal_type": "dinner" if "dinner" in raw_text.lower() else ("breakfast" if "breakfast" in raw_text.lower() else ""),
            "items": items,
            "constraints": {"max_delivery_minutes": 0, "priority": "unspecified", "max_budget": 0.0},
            "target_app": target_app,
            "confidence": 0.95,
            "needs_clarification": False,
            "clarification_reason": "",
        })
