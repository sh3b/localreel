import prettier from 'eslint-config-prettier';
import path from 'node:path';
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import { defineConfig, includeIgnoreFile } from 'eslint/config';
import globals from 'globals';
import ts from 'typescript-eslint';

const gitignorePath = path.resolve(import.meta.dirname, '.gitignore');

export default defineConfig(
	includeIgnoreFile(gitignorePath),
	js.configs.recommended,
	ts.configs.recommended,
	svelte.configs.recommended,
	prettier,
	svelte.configs.prettier,
	{
		languageOptions: { globals: { ...globals.browser, ...globals.node } },
		rules: {
			// typescript-eslint strongly recommend that you do not use the no-undef lint rule on TypeScript projects.
			// see: https://typescript-eslint.io/troubleshooting/faqs/eslint/#i-get-errors-from-the-no-undef-rule-about-global-variables-not-being-defined-even-though-there-are-no-typescript-errors
			'no-undef': 'off'
		}
	},
	{
		files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
		languageOptions: {
			parserOptions: {
				projectService: true,
				extraFileExtensions: ['.svelte'],
				parser: ts.parser
			}
		}
	},
	// The layer rules in docs/frontend-patterns.md that a linter can check.
	{
		// Server calls belong in state classes (lib/**/*.svelte.ts); pages and
		// components import only the API's types.
		files: ['src/routes/**', 'src/lib/components/**'],
		rules: {
			'no-restricted-imports': [
				'error',
				{
					paths: [
						{
							name: '#lib/api/client.ts',
							importNames: ['api'],
							message: 'Call the server from a state class in lib/ (see VideoStream, AddQueue).'
						}
					]
				}
			]
		}
	},
	{
		// Looks come from the theme tokens and the shared classes in buttons.ts,
		// and a page's own <style> never reaches the components it renders.
		files: ['src/routes/**/*.svelte'],
		rules: {
			'no-restricted-syntax': [
				'error',
				{
					selector: 'SvelteStyleElement',
					message: 'Pages have no <style>: use theme tokens or the classes in buttons.ts.'
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
