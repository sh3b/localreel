/** @type {import("prettier").Config} */
const config = {
	useTabs: true,
	singleQuote: true,
	trailingComma: 'none',
	printWidth: 100,
	// Import order as Immich's web app sorts it (packages, Node built-ins, the
	// app's own aliases, then relative paths); ours also has `#lib`. Tailwind's
	// plugin must stay last.
	plugins: [
		'@ianvs/prettier-plugin-sort-imports',
		'prettier-plugin-svelte',
		'prettier-plugin-tailwindcss'
	],
	importOrder: ['<THIRD_PARTY_MODULES>', '<BUILTIN_MODULES>', '^[$#]', '^[./]'],
	overrides: [{ files: '*.svelte', options: { parser: 'svelte' } }],
	tailwindStylesheet: './src/app.css'
};

export default config;
