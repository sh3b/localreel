import svelteConfig from '@sveltejs/eslint-config';
import { defineConfig, includeIgnoreFile } from 'eslint/config';
import ts from 'typescript-eslint';
import path from 'node:path';

const gitignorePath = path.resolve(import.meta.dirname, '.gitignore');

export default defineConfig(
	includeIgnoreFile(gitignorePath),
	// The Svelte team's shared config (what SvelteKit itself lints with): the
	// recommended JS, TypeScript and Svelte rules, Prettier, and their house rules.
	svelteConfig,
	{
		rules: {
			// TypeScript checks for undefined names; typescript-eslint advises turning this off.
			'no-undef': 'off',
			// The shared config turns these off; the project template had them on, and
			// `any` or a silenced type error should stay visible in review.
			'@typescript-eslint/no-explicit-any': 'error',
			'@typescript-eslint/ban-ts-comment': 'error'
		}
	},
	{
		// `let { … } = $props()` is how Svelte components take props; the Svelte
		// plugin's version of prefer-const understands runes.
		files: ['**/*.svelte', '**/*.svelte.ts'],
		rules: {
			'prefer-const': 'off',
			'svelte/prefer-const': ['error', { destructuring: 'all' }]
		}
	},
	{
		// Type-aware rules need type information for plain .ts files too.
		files: ['**/*.ts'],
		languageOptions: { parserOptions: { projectService: true, parser: ts.parser } }
	},
	{
		// A promise nobody awaits or catches fails silently, so every promise must
		// be awaited, returned or caught.
		files: ['**/*.ts', '**/*.svelte'],
		rules: {
			'@typescript-eslint/no-floating-promises': 'error',
			'@typescript-eslint/no-misused-promises': 'error',
			'@typescript-eslint/await-thenable': 'error',
			'@typescript-eslint/require-await': 'error'
		}
	},
	{
		// Looks come from the theme tokens, and a page's own <style> never reaches
		// the components it renders.
		files: ['src/routes/**/*.svelte'],
		rules: {
			'no-restricted-syntax': [
				'error',
				{
					selector: 'SvelteStyleElement',
					message: 'Pages have no <style>: use the theme tokens.'
				}
			]
		}
	},
	{
		rules: {
			// A button inside a form submits it unless it says otherwise.
			'svelte/button-has-type': 'error'
		}
	}
);
