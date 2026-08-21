"""Tests for app.core.llm.prompts.PromptManager."""

from pathlib import Path

import pytest

from app.core.llm.prompts import PromptManager, PromptTemplateNotFoundError


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    (tmp_path / "greeting.txt").write_text(
        "Hello, $name! Your schema is: $schema", encoding="utf-8"
    )
    return tmp_path


def test_render_substitutes_variables(templates_dir: Path) -> None:
    manager = PromptManager(templates_dir=templates_dir)

    result = manager.render("greeting", name="World", schema="{}")

    assert result == "Hello, World! Your schema is: {}"


def test_render_handles_json_braces_without_conflict(templates_dir: Path) -> None:
    """The whole reason $var syntax was chosen over str.format()."""

    manager = PromptManager(templates_dir=templates_dir)
    schema_with_braces = '{"type": "object", "properties": {"x": {"type": "string"}}}'

    result = manager.render("greeting", name="World", schema=schema_with_braces)

    assert schema_with_braces in result


def test_missing_template_raises_clear_error(templates_dir: Path) -> None:
    manager = PromptManager(templates_dir=templates_dir)

    with pytest.raises(PromptTemplateNotFoundError):
        manager.render("does_not_exist", name="x", schema="{}")


def test_missing_variable_raises_key_error(templates_dir: Path) -> None:
    manager = PromptManager(templates_dir=templates_dir)

    with pytest.raises(KeyError):
        manager.render("greeting", name="World")  # missing `schema`


def test_templates_are_cached_after_first_load(templates_dir: Path) -> None:
    manager = PromptManager(templates_dir=templates_dir)
    manager.render("greeting", name="A", schema="{}")

    # Mutate the file on disk; cached render should NOT pick up the change.
    (templates_dir / "greeting.txt").write_text("CHANGED $name $schema", encoding="utf-8")

    result = manager.render("greeting", name="B", schema="{}")
    assert result == "Hello, B! Your schema is: {}"
