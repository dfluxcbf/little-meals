from __future__ import annotations

import pytest

from little_meals.store.frontmatter import FrontmatterError, render, slugify, split


@pytest.mark.requirement("REQ-000000001")
def test_split_round_trips_with_render():
    yaml_str, body = split(render({"name": "Soup", "servings": 2}, "1. Boil water.\n"))
    assert "name: Soup" in yaml_str
    assert body == "1. Boil water.\n"


def test_split_tolerates_missing_frontmatter():
    yaml_str, body = split("just a plain markdown file\nwith no frontmatter\n")
    assert yaml_str == ""
    assert body == "just a plain markdown file\nwith no frontmatter\n"


def test_split_rejects_unterminated_frontmatter():
    with pytest.raises(FrontmatterError):
        split("---\nname: Soup\nno closing fence here\n")


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Lemon Garlic Chicken", "lemon-garlic-chicken"),
        ("Crème brûlée", "creme-brulee"),
        ("  spaced -- out  ", "spaced-out"),
        ("!!!", "recipe"),
        ("", "recipe"),
    ],
)
def test_slugify(name, expected):
    assert slugify(name) == expected
