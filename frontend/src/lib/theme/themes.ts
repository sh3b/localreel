// Every theme defined in tokens.css. The first one is the default.
export const THEMES = [
	{ id: 'tool', label: 'dark' },
	{ id: 'tool-light', label: 'light' }
] as const;

export type ThemeId = (typeof THEMES)[number]['id'];

// Also read by the inline script in app.html, which applies the saved theme
// before the first paint so the page never flashes the wrong colours.
export const THEME_STORAGE_KEY = 'localreel.theme';

export function isThemeId(value: unknown): value is ThemeId {
	return THEMES.some((theme) => theme.id === value);
}

export function resolveTheme(saved: string | null): ThemeId {
	return isThemeId(saved) ? saved : THEMES[0].id;
}

export function nextTheme(current: ThemeId): ThemeId {
	const index = THEMES.findIndex((theme) => theme.id === current);
	return THEMES[(index + 1) % THEMES.length].id;
}

export function readSavedTheme(): ThemeId {
	try {
		return resolveTheme(localStorage.getItem(THEME_STORAGE_KEY));
	} catch {
		return THEMES[0].id;
	}
}

export function applyTheme(theme: ThemeId): void {
	document.documentElement.dataset.theme = theme;
	try {
		localStorage.setItem(THEME_STORAGE_KEY, theme);
	} catch {
		// Private windows can refuse storage; the theme still applies for this visit.
	}
}
