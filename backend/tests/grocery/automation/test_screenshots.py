"""Tests for app.grocery.automation.screenshots.capture_screenshot."""

from pathlib import Path

from app.grocery.automation.screenshots import capture_screenshot


class _FakeDriver:
    def __init__(self) -> None:
        self.saved_path: str | None = None

    def get_screenshot_as_file(self, path: str) -> bool:
        self.saved_path = path
        Path(path).touch()  # simulate the file Appium would have written
        return True


def test_capture_screenshot_creates_file_with_label_and_png_suffix(tmp_path: Path) -> None:
    driver = _FakeDriver()

    result_path = capture_screenshot(driver, "search_failed", output_dir=tmp_path)

    assert result_path.exists()
    assert "search_failed" in result_path.name
    assert result_path.suffix == ".png"
    assert driver.saved_path == str(result_path)


def test_capture_screenshot_sanitizes_unsafe_label_characters(tmp_path: Path) -> None:
    driver = _FakeDriver()

    result_path = capture_screenshot(driver, "zepto/onion search!", output_dir=tmp_path)

    assert "/" not in result_path.name
    assert "!" not in result_path.name
    assert " " not in result_path.name


def test_capture_screenshot_creates_output_dir_if_missing(tmp_path: Path) -> None:
    driver = _FakeDriver()
    nested = tmp_path / "nested" / "dir"

    result_path = capture_screenshot(driver, "x", output_dir=nested)

    assert nested.exists()
    assert result_path.exists()


def test_capture_screenshot_filenames_are_unique_across_calls(tmp_path: Path) -> None:
    driver = _FakeDriver()

    path1 = capture_screenshot(driver, "same_label", output_dir=tmp_path)
    path2 = capture_screenshot(driver, "same_label", output_dir=tmp_path)

    assert path1 != path2
