# localreel web UI

SvelteKit (client-only, built to static files) + Tailwind.

## Develop

```bash
make fe-install          # once
make fe-dev              # http://localhost:5173
```

Checks: `make fe-check` (Prettier, ESLint, svelte-check), `make fe-test`
(Vitest), `make fe-build`.

## Where things are

| Path                       | What                                               |
| -------------------------- | -------------------------------------------------- |
| `src/lib/theme/tokens.css` | Every colour, font and size, per theme             |
| `src/lib/theme/themes.ts`  | The list of themes, saving and applying the choice |
| `src/app.css`              | Maps the tokens onto Tailwind utilities            |
| `src/lib/shell/`           | Shared chrome: nav and keyboard shortcuts          |
| `src/lib/components/`      | Reusable pieces                                    |
| `src/routes/`              | One folder per page                                |

Imports use the `#lib/...` subpath alias with the file extension, for example
`import { NAV } from '#lib/shell/nav.ts'`.

## Change the look

Components never use raw colours or fonts. They use utilities such as
`bg-bg`, `text-muted`, `border-line` and `text-accent`, which read CSS
variables from `tokens.css`.

- **Tweak the current theme:** edit its block in `tokens.css`.
- **Add a theme:** copy a `[data-theme]` block in `tokens.css`, rename it, change
  the values, then add it to `THEMES` in `themes.ts`. The theme button in the
  top bar cycles through `THEMES`; `static/theme.js` applies the saved one
  before the first paint and needs no change.
- **Add a token:** define `--lr-name` in every theme block, then map it in the
  `@theme inline` block in `app.css` (`--color-name: var(--lr-name);`, or
  `--text-name` for a type size, `--spacing-name` for a length).
