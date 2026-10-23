# localreel web UI

SvelteKit (client-only, built to static files) + Tailwind. In the compose stack,
nginx serves the build at `/`, the API at `/api/` and the media at `/media/`.

## Develop

```bash
make fe-install          # once
docker compose up -d     # a running localreel to talk to
make fe-dev              # http://localhost:5173
```

The dev server proxies `/api` and `/media` to `http://127.0.0.1:8080` (the
compose stack). Point it elsewhere with `LOCALREEL_URL=http://host:port`.

Checks, as CI runs them: `make fe-check` (Prettier, ESLint, svelte-check),
`make fe-test` (Vitest), `make fe-build`.

## Where things are

| Path                       | What                                               |
| -------------------------- | -------------------------------------------------- |
| `src/lib/theme/tokens.css` | Every colour, font and size, per theme             |
| `src/lib/theme/themes.ts`  | The list of themes, saving and applying the choice |
| `src/app.css`              | Maps the tokens onto Tailwind utilities            |
| `src/lib/api/`             | Typed API client, generated from FastAPI's schema  |
| `src/lib/shell/`           | Shared chrome: nav, status line, keyboard hints    |
| `src/lib/components/`      | Reusable pieces                                    |
| `src/routes/`              | One folder per page                                |

Imports use the `#lib/...` subpath alias with the file extension, for example
`import { api } from '#lib/api/client.ts'`.

## Change the look

Components never use raw colours or fonts. They use utilities such as
`bg-surface`, `text-muted`, `border-line`, `text-accent` and `font-title`, which
read CSS variables from `tokens.css`.

- **Tweak the current theme:** edit its block in `tokens.css`.
- **Add a theme:** copy a `[data-theme]` block in `tokens.css`, rename it, change
  the values, then add it to `THEMES` in `themes.ts`. The theme button in the
  top bar cycles through `THEMES`; `static/theme.js` applies the saved one
  before the first paint and needs no change.
- **Add a token:** define `--lr-name` in every theme block, then map it in the
  `@theme inline` block in `app.css` (`--color-name: var(--lr-name);`, or
  `--text-name` for a type size, `--spacing-name` for a length).

Text and marks over a video or thumbnail (`text-on-media`, `from-scrim/90`,
`text-media-accent`) sit on a dark scrim in every theme, so a light theme keeps
those tokens light-on-dark.

## API types

`src/lib/api/openapi.json` and `schema.d.ts` are generated. After changing an
endpoint or a DTO in the backend, run `make openapi` from the repository root
and commit both files.
