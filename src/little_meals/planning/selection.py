from __future__ import annotations

import random
from typing import Optional

from little_meals.models import Preference, Recipe


def select_recipes_for_plan(
    recipes: list[Recipe],
    recipes_per_week: int,
    rng: Optional[random.Random] = None,
) -> list[Recipe]:
    """The Milestone 3 selection engine: fills a plan from the existing
    recipe library, excluding disliked recipes, up to `recipes_per_week`.

    Milestone 4 adds AI-suggested recipes on top of this when the library
    doesn't have enough liked recipes to fill every slot - this function
    only ever draws from what's already in `recipes`, so a library with
    fewer liked recipes than `recipes_per_week` yields a shorter plan rather
    than padding it with anything invented.

    Selection is randomized (not just the first N) so a household with a
    library bigger than `recipes_per_week` sees variety week to week, not
    the same fixed subset every time. Pass `rng` for deterministic tests.
    """
    liked = [recipe for recipe in recipes if recipe.preference == Preference.LIKED]
    count = max(0, recipes_per_week)
    if len(liked) <= count:
        return liked

    rng = rng or random.Random()
    return rng.sample(liked, k=count)
