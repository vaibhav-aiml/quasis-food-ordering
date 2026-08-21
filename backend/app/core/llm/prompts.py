"""Prompt template loading and rendering.

Templates are plain ``.txt`` files using ``string.Template``'s ``$variable``
syntax (not ``str.format()``/f-strings) — deliberately, because prompts in
this project embed JSON schemas, and a JSON schema is full of literal
``{`` ``}`` characters that would collide with ``.format()``'s placeholder
syntax. See Phase 3 design notes.
"""

from collections.abc import Sequence
from pathlib import Path
from string import Template

DEFAULT_TEMPLATES_DIRS: list[Path] = [
    Path(__file__).parent.parent.parent / "grocery" / "prompts",
    Path(__file__).parent.parent.parent / "food_ordering" / "prompts",
]


class PromptTemplateNotFoundError(Exception):
    """Raised when a named template doesn't exist on disk."""


class PromptManager:
    """Loads prompt templates from disk and renders them with variables."""

    def __init__(
        self, templates_dir: Path | Sequence[Path] | None = None
    ) -> None:
        if templates_dir is None:
            self._templates_dirs = list(DEFAULT_TEMPLATES_DIRS)
        elif isinstance(templates_dir, Path):
            self._templates_dirs = [templates_dir]
        else:
            self._templates_dirs = list(templates_dir)
        self._cache: dict[str, Template] = {}

    def _load(self, name: str) -> Template:
        if name in self._cache:
            return self._cache[name]

        for directory in self._templates_dirs:
            path = directory / f"{name}.txt"
            if path.is_file():
                template = Template(path.read_text(encoding="utf-8"))
                self._cache[name] = template
                return template

        raise PromptTemplateNotFoundError(
            f"No prompt template named '{name}' found in {[str(d) for d in self._templates_dirs]}"
        )

    def render(self, template_name: str, **variables: str) -> str:
        """Render a named template with the given variables.

        Note the parameter is ``template_name``, not ``name`` — a template
        is entitled to define its own ``$name`` substitution variable, and
        that must never collide with the argument used to select *which*
        template to load.

        Raises:
            PromptTemplateNotFoundError: if ``template_name`` doesn't match
                a file under the templates directory.
            KeyError: if the template references a ``$variable`` that
                wasn't supplied — surfaced as-is (via ``Template.substitute``,
                not ``safe_substitute``) so a missing variable is a loud
                failure at render time, not a silently broken prompt sent
                to the model.
        """

        template = self._load(template_name)
        return template.substitute(**variables)
