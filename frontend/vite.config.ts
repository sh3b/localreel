import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';

// In development the UI talks to a running localreel (the compose stack by
// default), so /api and /media behave exactly as they do behind nginx.
const backend = process.env.LOCALREEL_URL ?? 'http://127.0.0.1:8080';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Runes everywhere in our code; libraries keep their own mode.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			// Single-page app: every unknown path gets index.html and the client routes it.
			adapter: adapter({ fallback: 'index.html' }),
			// Written into index.html as a <meta> tag, with hashes for SvelteKit's own
			// inline scripts. Only scripts from this site run, so injected markup
			// can't execute. Inline styles stay allowed: Svelte sets some itself and
			// they cannot run code. frame-ancestors is ignored in a <meta> tag, so
			// nginx.conf sends that one as a header.
			csp: {
				mode: 'hash',
				directives: {
					'default-src': ['self'],
					'script-src': ['self'],
					'style-src': ['self', 'unsafe-inline'],
					'img-src': ['self', 'data:'],
					'media-src': ['self'],
					'connect-src': ['self'],
					'object-src': ['none'],
					'base-uri': ['self'],
					'form-action': ['self']
				}
			}
		})
	],
	server: {
		proxy: {
			'/api': backend,
			'/media': backend
		}
	},
	test: {
		expect: { requireAssertions: true },
		environment: 'node',
		include: ['src/**/*.spec.ts']
	}
});
