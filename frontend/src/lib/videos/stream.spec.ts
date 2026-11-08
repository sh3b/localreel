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
	function remove(id: string): Promise<void> {
		all.splice(
			all.findIndex((c) => c.id === id),
			1
		);
		return Promise.resolve();
	}
	return { page, remove, requests };
}

const neverRemoves = () => Promise.resolve();

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
			remove: neverRemoves,
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
			remove: neverRemoves,
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
			remove: neverRemoves,
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
			remove: neverRemoves,
			page: () => Promise.reject(new Error('The server did not answer.'))
		});

		await stream.ensureLoaded();

		expect(stream.items).toHaveLength(0);
		expect(stream.loadFailed).toBe(true);
		expect(stream.loading).toBe(false);
	});

	it('removes a video and stays on the one shown', async () => {
		const server = fakeServer(5);
		const stream = new VideoStream(server);
		await stream.ensureLoaded();
		await stream.go(3);

		await stream.remove('id-1');

		expect(stream.items.map((v) => v.id)).toEqual(['id-0', 'id-2', 'id-3', 'id-4']);
		expect(stream.current?.id).toBe('id-3');
		expect(stream.removing).toBe(false);
	});

	it('shows the next video after removing the one shown, or the last one at the end', async () => {
		const stream = new VideoStream(fakeServer(3));
		await stream.ensureLoaded();
		await stream.go(1);

		await stream.remove('id-1');
		expect(stream.current?.id).toBe('id-2');

		await stream.remove('id-2');
		expect(stream.current?.id).toBe('id-0');
	});

	it('loads the next page when a removal leaves the list short', async () => {
		const server = fakeServer(30);
		const stream = new VideoStream(server);
		await stream.ensureLoaded();
		await stream.go(20);
		expect(stream.items).toHaveLength(24);

		await stream.remove('id-20');

		expect(stream.items).toHaveLength(29);
		expect(stream.current?.id).toBe('id-21');
	});

	it('keeps the video and reports when the server does not remove it', async () => {
		const stream = new VideoStream({
			...fakeServer(3),
			remove: () => Promise.reject(new Error('The server did not remove it.'))
		});
		await stream.ensureLoaded();

		await stream.remove('id-1');

		expect(stream.items).toHaveLength(3);
		expect([stream.removeFailed, stream.removing]).toEqual([true, false]);
	});

	it('gives up on a remove the server never answers', async () => {
		vi.useFakeTimers();
		const stream = new VideoStream({
			...fakeServer(3),
			remove: (_id, signal) =>
				new Promise((_, reject) => {
					signal.addEventListener('abort', () => reject(new Error('aborted')));
				})
		});
		await stream.ensureLoaded();

		const removed = stream.remove('id-1');
		await vi.advanceTimersByTimeAsync(10_000);
		await removed;

		expect([stream.removeFailed, stream.removing]).toEqual([true, false]);
		expect(stream.items).toHaveLength(3);
	});

	it('gives up on a page the server never answers', async () => {
		vi.useFakeTimers();
		const stream = new VideoStream({
			remove: neverRemoves,
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
