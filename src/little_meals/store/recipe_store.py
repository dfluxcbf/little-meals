from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from little_meals.llm.extraction import ExtractionError, RecipeExtractionService
from little_meals.llm.ollama_client import OllamaUnavailable
from little_meals.models import Preference, Recipe
from little_meals.store.frontmatter import FrontmatterError, render, slugify, split

logger = logging.getLogger(__name__)

_STEP_PREFIX_RE = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+")


class RecipeStoreError(RuntimeError):
    """Base error for the recipe store."""


class RecipeNotFound(RecipeStoreError):
    def __init__(self, recipe_id: str):
        super().__init__(f"Recipe not found: {recipe_id}")
        self.recipe_id = recipe_id


class RecipeStore:
    """Reads/writes recipes as Markdown+YAML-frontmatter files.

    The directory is the source of truth - there is no cache, so a file the
    user hand-edits outside the app is picked up the next time it's read.
    """

    def __init__(self, recipes_dir: Path):
        self._dir = Path(recipes_dir)

    def list(self, extractor: Optional[RecipeExtractionService] = None) -> list[Recipe]:
        """List every recipe in the directory.

        A file that doesn't parse as a valid recipe (missing/broken
        frontmatter, a hand-dropped-in foreign format, a field of the wrong
        shape) is normalized through `extractor` when one is given: its raw
        text is run through the same LLM extraction pipeline a manual
        submission uses, and the result is rewritten to the file in
        canonical frontmatter form, so every later read - with or without an
        extractor - hits the fast path. Only if that also fails (or no
        extractor was given) is the file skipped, same as before.
        """
        self._dir.mkdir(parents=True, exist_ok=True)
        recipes: list[Recipe] = []
        for path in sorted(self._dir.glob("*.md")):
            try:
                recipes.append(self._read(path))
                continue
            except (FrontmatterError, ValueError, KeyError, TypeError) as exc:
                read_exc = exc
            normalized = self._normalize(path, extractor) if extractor is not None else None
            if normalized is not None:
                recipes.append(normalized)
            else:
                logger.warning("Skipping unparseable recipe file %s: %s", path, read_exc)
        return recipes

    def _normalize(self, path: Path, extractor: RecipeExtractionService) -> Optional[Recipe]:
        raw_text = path.read_text(encoding="utf-8")
        if not raw_text.strip():
            return None
        try:
            extracted = extractor.extract(raw_text)
        except (ExtractionError, OllamaUnavailable) as exc:
            logger.warning("Could not normalize recipe file %s via LLM extraction: %s", path, exc)
            return None
        recipe = Recipe.from_extracted(extracted, id=path.stem, source_text=raw_text, now=datetime.now(timezone.utc))
        self._write(recipe)
        logger.info("Normalized recipe file %s via LLM extraction", path)
        return recipe

    def get(self, recipe_id: str) -> Recipe:
        path = self._path_for(recipe_id)
        if not path.exists():
            raise RecipeNotFound(recipe_id)
        return self._read(path)

    def create(self, recipe: Recipe) -> Recipe:
        self._dir.mkdir(parents=True, exist_ok=True)
        base_slug = slugify(recipe.name)
        slug = base_slug
        suffix = 2
        while (self._dir / f"{slug}.md").exists():
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        stored = recipe.model_copy(update={"id": slug})
        self._write(stored)
        return stored

    def update(self, recipe_id: str, recipe: Recipe) -> Recipe:
        existing = self.get(recipe_id)
        stored = recipe.model_copy(
            update={
                "id": recipe_id,
                "created_at": existing.created_at,
                "updated_at": datetime.now(timezone.utc),
                "preference": existing.preference,
            }
        )
        self._write(stored)
        return stored

    def set_preference(self, recipe_id: str, preference: Preference) -> Recipe:
        existing = self.get(recipe_id)
        stored = existing.model_copy(update={"preference": preference, "updated_at": datetime.now(timezone.utc)})
        self._write(stored)
        return stored

    def delete(self, recipe_id: str) -> None:
        path = self._path_for(recipe_id)
        if not path.exists():
            raise RecipeNotFound(recipe_id)
        path.unlink()

    def count(self) -> int:
        """Number of recipe files in the directory, without parsing them -
        used by `lmeals import-spoonacular --reset` to report how many
        recipes a reset will delete before asking for confirmation."""
        self._dir.mkdir(parents=True, exist_ok=True)
        return len(list(self._dir.glob("*.md")))

    def delete_all(self) -> int:
        """Deletes every recipe file in the directory, including ones that
        fail to parse - used by `lmeals import-spoonacular --reset` to fully
        clear the library before a fresh import. Returns the number removed."""
        self._dir.mkdir(parents=True, exist_ok=True)
        paths = list(self._dir.glob("*.md"))
        for path in paths:
            path.unlink()
        return len(paths)

    def _path_for(self, recipe_id: str) -> Path:
        return self._dir / f"{recipe_id}.md"

    def _read(self, path: Path) -> Recipe:
        text = path.read_text(encoding="utf-8")
        yaml_str, body = split(text)
        if not yaml_str:
            raise FrontmatterError(f"{path} has no frontmatter")
        data = yaml.safe_load(yaml_str) or {}
        steps = _parse_steps(body)
        return Recipe(
            id=path.stem,
            name=data["name"],
            cook_time_minutes=data["cook_time_minutes"],
            classification=data["classification"],
            nutrition=data["nutrition"],
            servings=data.get("servings", 2),
            ingredients=data["ingredients"],
            steps=steps,
            preference=data.get("preference", "liked"),
            source_text=data.get("source_text"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    def _write(self, recipe: Recipe) -> None:
        path = self._path_for(recipe.id)
        frontmatter = {
            "name": recipe.name,
            "cook_time_minutes": recipe.cook_time_minutes,
            "classification": recipe.classification.value,
            "nutrition": recipe.nutrition.model_dump(exclude_none=True),
            "servings": recipe.servings,
            "ingredients": [ingredient.model_dump(exclude_none=True) for ingredient in recipe.ingredients],
            "preference": recipe.preference.value,
            "source_text": recipe.source_text,
            "created_at": recipe.created_at.isoformat(),
            "updated_at": recipe.updated_at.isoformat(),
        }
        body = _render_steps(recipe.steps)
        text = render(frontmatter, body)
        self._dir.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".md.tmp")
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(tmp_path, path)


def _render_steps(steps: list[str]) -> str:
    lines = [f"{index}. {step}" for index, step in enumerate(steps, start=1)]
    return "\n".join(lines) + "\n"


def _parse_steps(body: str) -> list[str]:
    steps = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        steps.append(_STEP_PREFIX_RE.sub("", stripped).strip())
    return steps
