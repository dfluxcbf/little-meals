from __future__ import annotations

import pytest

from little_meals.planning.glob_match import matches_glob

pytestmark = pytest.mark.requirement("REQ-000000063")


def test_none_pattern_matches_everything():
    assert matches_glob("garlic clove", None) is True


def test_blank_pattern_matches_everything():
    assert matches_glob("garlic clove", "   ") is True


def test_star_wildcard():
    assert matches_glob("garlic clove", "*garlic*") is True
    assert matches_glob("onion", "*garlic*") is False


def test_question_mark_wildcard():
    assert matches_glob("salt", "sal?") is True
    assert matches_glob("salsa", "sal?") is False


def test_case_insensitive():
    assert matches_glob("Garlic Clove", "*GARLIC*") is True


def test_pattern_is_stripped():
    assert matches_glob("garlic clove", "  garlic clove  ") is True
