"""Exception hierarchy for the Appium automation layer.

Mirrors the LLM layer's design (see app.core.llm.exceptions): callers
(Store Adapters, from Phase 7 onward) catch these typed errors, never raw
Appium/Selenium exceptions. This is the one place that translates
"something went wrong talking to the device" into project-specific
errors — matches Phase 0 architecture doc, section 12 (error handling
strategy).
"""


class AutomationError(Exception):
    """Base class for all automation-layer errors."""


class AutomationConnectionError(AutomationError):
    """Raised when an Appium session could not be started at all — server
    unreachable, invalid capabilities, device not found, etc.
    """


class AutomationTimeoutError(AutomationError):
    """Raised when waiting for an element/condition times out."""
