Vendored third-party JS, so the app has no runtime dependency on internet
access or a node/npm build step.

- `htmx.min.js` — htmx 1.9.12, fetched from
  `https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js`. Update by re-fetching
  that URL with a newer version pin and updating this line.
