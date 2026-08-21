"""Screenshot capture utility.

Per Phase 0 architecture doc, section 13 (logging strategy): screenshots
on automation errors are saved to disk and referenced by PATH in logs,
never inlined as base64. This module exists to give every future
automation call site — real error handling from Phase 7+ onward — one
consistent way to do that.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SCREENSHOT_DIR = Path("screenshots")  # gitignored (see .gitignore)


def capture_screenshot(
    driver: Any, label: str, output_dir: Path = DEFAULT_SCREENSHOT_DIR
) -> Path:
    """Save a screenshot of the current screen, returning its path.

    Filenames are ``{UTC timestamp}_{short unique suffix}_{sanitized
    label}.png`` — sortable by time, safe on any filesystem regardless of
    what characters ``label`` contains, and guaranteed-unique even across
    calls made within the same microsecond (a short ``uuid4`` suffix,
    rather than relying solely on timestamp resolution, which isn't
    guaranteed fine-grained enough on every system).
    """

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    unique_suffix = uuid.uuid4().hex[:6]
    safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
    path = output_dir / f"{timestamp}_{unique_suffix}_{safe_label}.png"

    driver.get_screenshot_as_file(str(path))
    return path
