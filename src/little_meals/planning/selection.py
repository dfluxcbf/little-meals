from __future__ import annotations

import random
from typing import Optional

from little_meals.models import Recipe


def select_recipes_for_plan(
    recipes: list[Recipe],
    recipes_per_week: int,
    rng: Optional[random.Random] = None,
) -> list[Recipe]:
    """The Milestone 3 selection engine: fills a plan from the existing
    recipe library, up to `recipes_per_week`. Only ever draws from what's
    already in `recipes`, so a library smaller than `recipes_per_week`
    yields a shorter plan rather than padding it with anything invented.

    Selection is randomized (not just the first N) so a household with a
    library bigger than `recipes_per_week` sees variety week to week, not
    the same fixed subset every time. Pass `rng` for deterministic tests.
    """
    count = max(0, recipes_per_week)
    if len(recipes) <= count:
        return list(recipes)

    rng = rng or random.Random()
    return rng.sample(recipes, k=count)
