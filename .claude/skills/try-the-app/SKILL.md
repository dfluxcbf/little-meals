---
name: try-the-app
description: Runs little-meals from this checkout on port 8766 with a scratch data dir, to try a change in the real app or take screenshots of it without touching the household's live server on 8765. Use after changing a page, a template, the static assets or the API, before calling the change done.
---

# Try the app

The household's own server (little-workshop's, port 8765) holds real data, so a change is tried on a separate
server. Start it in the background:

```
python3 .claude/skills/try-the-app/scripts/serve_scratch.py
```

It serves this checkout's `src/` (no install needed) at `http://127.0.0.1:8766` with a fresh data dir in the
system temp folder, and prints both. `--port N` and `--data-dir PATH` override them; reusing a data dir keeps
what earlier runs created. It refuses port 8765 and a port already in use. Stop the background task when done.

For a page, check it at a desktop size and at a phone size (about 390x844): the layout differs between them.
`docs/ui_design.md` is what the pages should look like.
