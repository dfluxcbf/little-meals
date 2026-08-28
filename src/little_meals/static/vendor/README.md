Vendored third-party JS and fonts, so the app has no runtime dependency on
internet access, a node/npm build step, or a third-party CDN (Google Fonts
included — see `docs/ui_design.md`'s typography section for why).

- `htmx.min.js` — htmx 1.9.12, fetched from
  `https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js`. Update by re-fetching
  that URL with a newer version pin and updating this line.
- `fonts/fraunces-variable-latin.woff2`, `fonts/inter-variable-latin.woff2` —
  Fraunces v38 and Inter v20, latin-subset variable fonts (weights 400-700 in
  one file each), fetched from `fonts.gstatic.com` via the Google Fonts css2
  API and re-served locally through `static/fonts.css`. Both are licensed
  under the SIL Open Font License 1.1 (see each family's OFL.txt at
  [Fraunces](https://github.com/undercasetype/Fraunces) /
  [Inter](https://github.com/rsms/inter)), which permits redistribution.
  Update by re-fetching
  `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&display=swap`
  with a browser user-agent and re-downloading the `latin`-subset `src` URLs.
