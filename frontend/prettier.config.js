/** @type {import("prettier").Config} */
const config = {
	useTabs: true,
	singleQuote: true,
	trailingComma: 'none',
	printWidth: 100,
	// Import order: packages, Node built-ins, the app's own aliases (`#lib`
	// included), then relative paths. Tailwind's plugin must stay last.
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
