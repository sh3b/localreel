// Applies the saved theme before the first paint, so the page never flashes the
// wrong colours. Loaded as a file, not inline, so the CSP can stay script-src
// 'self'. An unknown name is harmless: tokens.css falls back to the default.
// The key is THEME_STORAGE_KEY in src/lib/theme/themes.ts.
try {
	const saved = localStorage.getItem('localreel.theme');
	if (saved) document.documentElement.dataset.theme = saved;
} catch {
	// Storage can be blocked (private windows); the default theme stays.
}
