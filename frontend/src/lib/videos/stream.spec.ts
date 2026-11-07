import { afterEach, describe, expect, it, vi } from 'vitest';
import type { VideoCard, VideoPage } from '#lib/api/client.ts';
import { VideoStream, type PageRequest } from './stream.svelte.ts';

function card(n: number): VideoCard {
	return {
		id: `id-${n}`,
		title: `Video ${n}`,
		uploader: null,
		duration_sec: 10,
		width: 1080,
		height: 1920,
		source: 'YOUTUBE',
		source_url: `https://youtu.be/${n}`,
		saved_at: '2026-11-01T00:00:00Z',
		playback_url: `/media/${n}.webm`,
		thumbnail_url: `/media/${n}.webp`
	};
}

// A server holding `total` videos, answering pages like GET /videos.
function fakeServer(total: number) {
	const requests: PageRequest[] = [];
	const all = Array.from({ length: total }, (_, i) => card(i));
	function page(request: PageRequest): Promise<VideoPage> {
		requests.push(request);
		const start = request.after ? all.findIndex((c) => c.id === request.after) + 1 : 0;
		const items = all.slice(start, start + request.limit);
		const more = start + request.limit < all.length;
		return Promise.resolve({ items, next_cursor: more ? items[items.length - 1].id : null });
	}
	return { page, requests };
}

describe('VideoStream', () => {
	afterEach(() => {
		vi.useRealTimers();
	});

	it('loads the first page once and knows when the list is complete', async () => {
		const server = fakeServer(5);
		const stream = new VideoStream(server);

		await stream.ensureLoaded();
		await stream.ensureLoaded();

		expect(stream.items).toHaveLength(5);
		expect(stream.complete).toBe(true);
		expect(server.requests).toHaveLength(1);
	});

	it('loads the next page from the cursor when the feed nears the end', async () => {
		const server = fakeServer(30);
		const stream = new VideoStream(server);
		await stream.ensureLoaded();

		await stream.go(21);

		expect(stream.items).toHaveLength(30);
		expect(server.requests[1].after).toBe('id-23');
		expect(stream.complete).toBe(true);
	});

	it('keeps the position inside the list', async () => {
		const stream = new VideoStream(fakeServer(3));
		await stream.ensureLoaded();

		await stream.step(-1);
		expect(stream.position).toBe(0);

		await stream.go(10);
		expect(stream.position).toBe(2);
		expect(stream.atEnd).toBe(true);
	});

	it('starts over in the new order', async () => {
		const server = fakeServer(3);
		const stream = new VideoStream(server);
		await stream.ensureLoaded();
		await stream.go(2);

		await stream.restart('oldest');

		expect(stream.position).toBe(0);
		expect(server.requests.at(-1)).toMatchObject({ sort: 'oldest', after: null });
	});

	it('keeps only the new order when restarted while a page is still loading', async () => {
		const answers: Array<() => void> = [];
		const all = fakeServer(3);
		const stream = new VideoStream({
			page: (request) => new Promise((resolve) => answers.push(() => resolve(all.page(request))))
		});

		const first = stream.restart('newest');
		const second = stream.restart('oldest');
		answers.forEach((answer) => answer());
		await Promise.all([first, second]);

		expect(all.requests.map((r) => r.sort)).toEqual(['newest', 'oldest']);
		expect(stream.items).toHaveLength(3);
		expect(stream.sort).toBe('oldest');
		expect(stream.loading).toBe(false);
		expect(stream.loadFailed).toBe(false);
	});

	it('finishes a move past the last loaded video once the next page is in', async () => {
		const server = fakeServer(30);
		let failNext = false;
		const stream = new VideoStream({
			page: (request) => {
				if (failNext) {
					failNext = false;
					return Promise.reject(new Error('The server did not answer.'));
				}
				return server.page(request);
			}
		});
		await stream.ensureLoaded();
		failNext = true;
		await stream.go(23);

		await stream.step(1);

		expect(stream.items).toHaveLength(30);
		expect(stream.position).toBe(24);
	});

	it('finishes a move past the last loaded video while that page is loading', async () => {
		const server = fakeServer(30);
		const answers: Array<() => void> = [];
		const stream = new VideoStream({
			page: (request) => new Promise((resolve) => answers.push(() => resolve(server.page(request))))
		});
		const loaded = stream.ensureLoaded();
		answers.shift()?.();
		await loaded;

		const prefetch = stream.go(23);
		const skip = stream.step(1);
		answers.shift()?.();
		await Promise.all([prefetch, skip]);

		expect(stream.items).toHaveLength(30);
		expect(stream.position).toBe(24);
	});

	it('keeps what it has and reports when a page fails', async () => {
		const stream = new VideoStream({
			page: () => Promise.reject(new Error('The server did not answer.'))
		});

		await stream.ensureLoaded();

		expect(stream.items).toHaveLength(0);
		expect(stream.loadFailed).toBe(true);
		expect(stream.loading).toBe(false);
	});

	it('gives up on a page the server never answers', async () => {
		vi.useFakeTimers();
		const stream = new VideoStream({
			page: (_request, signal) =>
				new Promise((_, reject) => {
					signal.addEventListener('abort', () => reject(new Error('aborted')));
				})
		});

		const loaded = stream.ensureLoaded();
		await vi.advanceTimersByTimeAsync(10_000);
		await loaded;

		expect(stream.loadFailed).toBe(true);
		expect(stream.loading).toBe(false);
	});
});
