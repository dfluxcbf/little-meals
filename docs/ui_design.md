# UI design

Visual design system for `little-meals`, established by the first UX draft
(published as a Claude Design canvas — link kept by the project owner, not
checked into the repo). This document is the durable, text-form record every
milestone builds against so the design survives independently of that link.

Concept: a **clean, cozy kitchen**. Three recurring metaphors carry the visual
identity instead of generic cards-and-forms chrome:

- The recipe library and the weekly plan are presented as pages in an **open
  cookbook**.
- A recipe's ingredient list hides behind a **fridge-door toggle** you open.
- The shopping list is a **paper note pinned to the fridge** (torn top edge,
  a magnet).
- Cook-along is a sequence of large, single-focus **step cards** — one step
  per screen, big type, minimal chrome.

"Clean" governs execution throughout: flat vector line icons (never emoji),
generous whitespace, no photographic texture — the metaphors are structural
and typographic, not skeuomorphic decoration.

## Design tokens

Colors are oklch(). Reuse these values verbatim; don't introduce new colors
without a reason tied to one of these roles.

| Role | Value | Used for |
|---|---|---|
| Cream (page background) | `oklch(97% 0.02 75)` | App background |
| Paper (surface) | `oklch(99% 0.012 85)` | Cards, inputs |
| Paper alt | `oklch(96% 0.015 80)` | Stepper pills, nested surfaces |
| Ink (primary text) | `oklch(24% 0.02 50)` | Headings, primary text |
| Ink soft (secondary text) | `oklch(46% 0.02 55)` | Meta text, labels |
| Ink faint (tertiary) | `oklch(66% 0.015 60)` | Disabled/unselected icons |
| Line (border) | `oklch(88% 0.015 70)` | Card borders, dividers |
| Terracotta (primary accent) | `oklch(58% 0.16 40)` | Primary buttons, active nav, logo |
| Terracotta soft | `oklch(93% 0.03 45)` | Badges (e.g. "Other" classification, cook-time chip) |
| Sage (positive) | `oklch(56% 0.09 150)` | Liked state, vegetarian tag, checked items |
| Sage soft | `oklch(93% 0.03 150)` | Liked/positive backgrounds |
| Rose (negative) | `oklch(58% 0.12 20)` | Disliked state |
| Rose soft | `oklch(93% 0.02 20)` | Disliked backgrounds |
| Teal | `oklch(55% 0.08 210)` | Pescetarian tag |
| Fridge blue-gray | `oklch(95% 0.015 220)` bg / `oklch(45% 0.03 220)` fg | Fridge-door ingredients panel only |

Typography: **Fraunces** (display — headings, recipe titles, the logotype;
fallback `Georgia, serif`) paired with **Inter** (body/UI text; fallback
`system-ui, sans-serif`). Both are open-license (SIL Open Font License) and
free to redistribute. The shipped app vendors the font files locally under
`static/vendor/` and serves them via `@font-face`, the same pattern already
used for `htmx.min.js` — no Google Fonts `<link>`, no third-party CDN call
on page load, consistent with the project's private-network posture
(Tailscale-only access, local LLM, no third-party APIs — see
`architecture.md`). The published design draft itself loads them from Google
Fonts for preview convenience only, since that's the one external font host
the draft's sandboxed preview environment permits; that shortcut doesn't
carry over to the real app.

## Screen-by-screen

| Screen | Metaphor / key pattern |
|---|---|
| Recipe library | 2-col card grid (desktop: 4-col with a left-rail nav instead of the bottom tab bar); spine-colored top edge by classification; tap-heart to like |
| Recipe detail | Like/dislike as a pair of thumb pills; servings stepper; steps as a numbered list; ingredients behind the fridge-door toggle |
| Recipe edit (new/edit) | Shared page for both "New recipe" (empty) and "Edit recipe" (pre-filled): name field, nutrition field, an ingredients table (name + quantity columns, add/remove row), a cooking-steps list (one row per step, add/remove row), save/cancel — see M12 in `milestones.md`. Supersedes the M1 free-text-paste → Ollama-extraction → preview-card flow described in earlier drafts of this doc. |
| Household settings | Grouped paper cards per section (meal rhythm, household size); sticky save with a confirmation toast |
| Weekly plan review | Open-cookbook layout, one meal per "page" row; no day-to-day scheduling — the household picks meals from the week's set in whatever order they like; like/dislike + per-meal servings; a pot-stamp toggle marks a meal cooked directly from this screen; whole-plan reroll, single-meal reroll, and controlled-reroll entry points per meal, all drawing from the existing library |
| Controlled reroll | Single-select list of 10 alternatives for one meal slot; sticky confirm button, disabled until a pick is made |
| Shopping list | Paper note pinned to a fridge (torn edge, magnet), one flat checklist (no grocery-category grouping), checkbox rows that strike through, cost-entry field |
| Cook-along | One big step card at a time, progress dots, prev/next; ends in a like/dislike prompt that feeds back into the recipe's preference state |

Shared shell: a 4-item bottom tab bar on mobile (Cookbook / This week /
Shopping / Settings) becomes a left rail on desktop. Recipe detail, the
recipe edit page (new/edit), the reroll picker, and cook-along are drill-in
screens (back chevron, no tab bar) reached from the four tab screens, not
tabs themselves.

**The pot stamp**: the top-right corner of a meal card holds a
toggleable "mark as cooked" control — a small pill with a pot icon.
Unmarked, it's an outline pill in muted ink. Marked, it flips to a
terracotta-inked, slightly rotated stamp look (dashed ring, small rotation)
reading "Cooked" — a deliberate rubber-stamp feel, distinct from the
sage/rose like-dislike colors so it never reads as a taste judgment, just a
completion mark.

## Implementation notes (Jinja2 + htmx, not a JS framework)

The design draft was built as a clickable prototype in a component-based
canvas tool for review purposes only. The actual frontend, per
`architecture.md`, stays server-rendered Jinja2 + vendored htmx — nothing
here changes that decision. Translate the prototype's interactions
accordingly, e.g.:

- **Fridge-door ingredient toggle**: a `<details>`/`<summary>` pair or a
  checkbox-driven CSS toggle — no JS framework needed, matches the
  progressive-enhancement approach already used for `recipe_detail.html`.
- **Like/dislike, checkboxes, steppers**: `hx-post`/`hx-patch` against the
  existing recipe/preferences/shopping-list APIs, swapping just the affected
  fragment (consistent with how M1's htmx wiring already works).
- **Cook-along step navigation**: server-rendered per-step fragments swapped
  via htmx, or plain anchor links to `#step-N` sections — no client-side
  step-index state required.

## Retrofit scope

M1 (recipe library, recipe detail, add recipe) and M2 (settings) already
shipped with placeholder styling (`system-ui`, unstyled tables/forms) before
this design existed. Restyling them to this system is its own milestone (see
`milestones.md`) rather than silently bundled into a later feature
milestone, so it stays tracked and requirement-linked like any other
implementation work. M1's "add recipe" screen was restyled by M9 but later
reworked functionally (not just visually) by M12, which replaced the
free-text/Ollama-extraction flow with the directly-editable recipe edit page
described above and added an equivalent "edit recipe" entry point.
