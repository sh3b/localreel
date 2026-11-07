import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import sirv from 'sirv';
import type { Plugin } from 'vite';
import { defineConfig } from 'vitest/config';
import path from 'node:path';
import process from 'node:process';

// Dev only, until nginx serves /media: the downloaded files, from the folder
// the worker writes to. A relative DOWNLOADS_DIR is taken from the repo root,
// where make runs the worker. sirv answers range requests, which a video
// needs to seek.
function serveMedia(): Plugin {
	const downloads = path.resolve(
		import.meta.dirname,
		'..',
		process.env.DOWNLOADS_DIR ?? 'data/downloads'
	);
	return {
		name: 'localreel-dev-media',
		configureServer(server) {
			server.middlewares.use('/media', sirv(downloads, { dev: true }));
		}
	};
}

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
			adapter: adapter({ fallback: 'index.html' })
		}),
		serveMedia()
	],
	server: {
		proxy: {
			// The API under /api, as the UI calls it; uvicorn serves it at the root.
			'/api': {
				target: 'http://127.0.0.1:8000',
				rewrite: (path) => path.replace(/^\/api/, '')
			}
		}
	},
	test: {
		expect: { requireAssertions: true },
		environment: 'node',
		include: ['src/**/*.spec.ts']
	}
});
