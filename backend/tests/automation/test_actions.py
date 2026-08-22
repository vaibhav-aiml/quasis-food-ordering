"""Tests for core atomic UI actions."""

from unittest.mock import MagicMock, patch
import pytest

from app.automation.actions import (
    click_element,
    find_element,
    get_element_text,
    is_element_present,
    press_key,
    scroll_to_element,
    set_text,
    wait_for_element,
)
from app.automation.exceptions import ElementNotFoundError


def test_find_element_success():
    mock_d = MagicMock()
    mock_elem = MagicMock()
    mock_elem.exists = True
    mock_d.return_value = mock_elem

    elem = find_element(mock_d, "home_search_bar", timeout=1.0)
    assert elem is not None


def test_wait_for_element_raises_on_timeout():
    mock_d = MagicMock()
    mock_elem = MagicMock()
    mock_elem.exists = MagicMock(return_value=False)
    mock_d.return_value = mock_elem
    mock_d.xpath.return_value = mock_elem

    with pytest.raises(ElementNotFoundError):
        wait_for_element(mock_d, "home_search_bar", timeout=0.2, poll_interval=0.05)


def test_click_element_success():
    mock_d = MagicMock()
    mock_elem = MagicMock()
    mock_elem.exists = True
    mock_d.return_value = mock_elem

    success = click_element(mock_d, "home_search_bar", timeout=1.0, retries=1)
    assert success is True
    mock_elem.click.assert_called_once()


def test_click_element_coordinate_fallback():
    mock_d = MagicMock()
    mock_elem = MagicMock()
    mock_elem.exists = True
    mock_elem.click.side_effect = Exception("Normal click failed")
    mock_elem.bounds = (100, 200, 300, 400)
    mock_d.return_value = mock_elem

    success = click_element(mock_d, "home_search_bar", timeout=1.0, retries=1)
    assert success is True
    mock_d.click.assert_called_with(200, 300)


def test_set_text_success():
    mock_d = MagicMock()
    mock_elem = MagicMock()
    mock_elem.exists = True
    mock_d.return_value = mock_elem

    success = set_text(mock_d, "search_input", text="Pizza", clear=True)
    assert success is True
    mock_elem.clear_text.assert_called_once()
    mock_elem.set_text.assert_called_with("Pizza")


def test_get_element_text():
    mock_d = MagicMock()
    mock_elem = MagicMock()
    mock_elem.exists = True
    mock_elem.get_text.return_value = "Domino's Pizza"
    mock_d.return_value = mock_elem

    text = get_element_text(mock_d, "restaurant_title")
    assert text == "Domino's Pizza"


def test_scroll_to_element_finds_on_swipe():
    mock_d = MagicMock()
    mock_elem = MagicMock()

    # First call False, second call True after swipe
    mock_elem_fail = MagicMock()
    mock_elem_fail.exists = False
    mock_elem_success = MagicMock()
    mock_elem_success.exists = True

    mock_d.side_effect = [mock_elem_fail, mock_elem_fail, mock_elem_success]

    elem = scroll_to_element(mock_d, "dish_title", max_swipes=2, direction="down")
    assert elem is not None
