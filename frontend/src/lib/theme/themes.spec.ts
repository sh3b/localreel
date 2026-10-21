import { describe, expect, it } from 'vitest';
import { THEMES, isThemeId, nextTheme, resolveTheme, type ThemeId } from './themes';

describe('resolveTheme', () => {
	it('keeps a saved theme that exists', () => {
		expect(resolveTheme('tool-light')).toBe('tool-light');
	});

	it('falls back to the default for nothing saved or an unknown name', () => {
		expect(resolveTheme(null)).toBe(THEMES[0].id);
		expect(resolveTheme('neon')).toBe(THEMES[0].id);
	});
});

describe('nextTheme', () => {
	it('cycles through every theme and wraps around', () => {
		let theme: ThemeId = THEMES[0].id;
		const seen: string[] = [];
		for (let i = 0; i < THEMES.length; i++) {
			seen.push(theme);
			theme = nextTheme(theme);
		}
		expect(seen).toEqual(THEMES.map((t) => t.id));
		expect(theme).toBe(THEMES[0].id);
	});
});

describe('isThemeId', () => {
	it('accepts registered themes only', () => {
		expect(isThemeId('tool')).toBe(true);
		expect(isThemeId(42)).toBe(false);
	});
});
