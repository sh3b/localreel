import { describe, expect, it } from 'vitest';
import type { VideoCard, VideoPage } from '#lib/api/client.ts';
import { VideoStream, type PageRequest } from './stream.svelte.ts';

function card(n: number): VideoCard {
	return {
		id: `id-${n}`,
		source: 'YOUTUBE',
		title: `Video ${n}`,
		uploader: null,
		tags: [],
		duration_sec: 10,
		width: 1080,
		height: 1920,
		source_url: null,
		source_view_count: null,
		saved_at: '2026-10-21T00:00:00Z',
		playback_url: `/media/${n}.mp4`,
		thumbnail_url: `/media/${n}.jpg`
	};
}

// A fake server holding `total` videos, answering pages like GET /videos.
function fakeServer(total: number) {
	const requests: PageRequest[] = [];
	const all = Array.from({ length: total }, (_, i) => card(i));
	async function load(request: PageRequest): Promise<VideoPage> {
		requests.push(request);
		const start = request.after ? all.findIndex((c) => c.id === request.after) + 1 : 0;
		const items = all.slice(start, start + request.limit);
		const more = start + request.limit < all.length;
		return { items, next_cursor: more ? items[items.length - 1].id : null };
	}
	return { load, requests };
}

describe('VideoStream', () => {
	it('loads the first page once and knows when the list is complete', async () => {
		const server = fakeServer(5);
		const stream = new VideoStream(server.load);

		await stream.ensureLoaded();
		await stream.ensureLoaded();

		expect(stream.items).toHaveLength(5);
		expect(stream.complete).toBe(true);
		expect(server.requests).toHaveLength(1);
	});

	it('loads the next page from the cursor when the feed nears the end', async () => {
		const server = fakeServer(30);
		const stream = new VideoStream(server.load);
		await stream.ensureLoaded();

		await stream.go(21);

		expect(stream.items).toHaveLength(30);
		expect(server.requests[1].after).toBe('id-23');
		expect(stream.complete).toBe(true);
	});

	it('keeps the position inside the list', async () => {
		const stream = new VideoStream(fakeServer(3).load);
		await stream.ensureLoaded();

		await stream.step(-1);
		expect(stream.position).toBe(0);

		await stream.go(10);
		expect(stream.position).toBe(2);
		expect(stream.atEnd).toBe(true);
	});

	it('starts over in the new order', async () => {
		const server = fakeServer(3);
		const stream = new VideoStream(server.load);
		await stream.ensureLoaded();
		await stream.go(2);

		await stream.restart('oldest');

		expect(stream.position).toBe(0);
		expect(server.requests.at(-1)).toMatchObject({ sort: 'oldest', after: null });
	});

	it('loads the new order when restarted while a page is still loading', async () => {
		const answers: Array<() => void> = [];
		const signals: AbortSignal[] = [];
		const all = fakeServer(3);
		const stream = new VideoStream((request, signal) => {
			signals.push(signal);
			return new Promise((resolve) => answers.push(() => resolve(all.load(request))));
		});

		const first = stream.restart('newest');
		const second = stream.restart('oldest');
		answers.forEach((answer) => answer());
		await Promise.all([first, second]);

		expect(signals[0].aborted).toBe(true);
		expect(all.requests.map((r) => r.sort)).toEqual(['newest', 'oldest']);
		expect(stream.items).toHaveLength(3);
		expect(stream.sort).toBe('oldest');
		expect(stream.loading).toBe(false);
		expect(stream.error).toBeNull();
	});

	it('finishes a move past the last loaded video once the next page is in', async () => {
		const server = fakeServer(30);
		let failNext = false;
		const stream = new VideoStream(async (request) => {
			if (failNext) {
				failNext = false;
				throw new Error('The server did not answer.');
			}
			return server.load(request);
		});
		await stream.ensureLoaded();
		failNext = true;
		await stream.go(23);

		await stream.step(1);

		expect(stream.items).toHaveLength(30);
		expect(stream.position).toBe(24);
	});

	it('keeps what it has and reports when a page fails', async () => {
		const stream = new VideoStream(async () => {
			throw new Error('The server did not answer.');
		});

		await stream.ensureLoaded();

		expect(stream.items).toHaveLength(0);
		expect(stream.error).toBe('The server did not answer.');
		expect(stream.loading).toBe(false);
	});
});
