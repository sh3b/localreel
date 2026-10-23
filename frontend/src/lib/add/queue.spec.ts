import { describe, expect, it } from 'vitest';
import type { QueueItem, SubmitResult } from '#lib/api/client.ts';
import { AddQueue, type QueueServer } from './queue.svelte.ts';

function item(id: string, status: QueueItem['status']): QueueItem {
	return {
		id,
		status,
		source_url: `https://youtu.be/${id}`,
		title: null,
		error_message: status === 'FAILED' ? 'HTTP 403' : null,
		saved_at: '2026-10-23T00:00:00Z'
	};
}

// A promise the test resolves or rejects when it chooses, to control the
// order in which answers arrive.
function deferred<T>() {
	let resolve!: (value: T) => void;
	let reject!: (error: Error) => void;
	const promise = new Promise<T>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

function server(overrides: Partial<QueueServer> = {}): QueueServer {
	return {
		queue: async () => [],
		submit: async () => [],
		retry: async () => {},
		...overrides
	};
}

const noNetwork = async () => {
	throw new TypeError('Failed to fetch');
};

describe('AddQueue', () => {
	it('shows a failed load when the server cannot be reached, and clears it once it answers', async () => {
		let reachable = false;
		const queue = new AddQueue(
			() => {},
			server({ queue: async () => (reachable ? [item('a', 'PENDING')] : noNetwork()) })
		);

		await queue.refresh();
		expect(queue.loadFailed).toBe(true);

		reachable = true;
		await queue.refresh();
		expect(queue.loadFailed).toBe(false);
		expect(queue.items.map((i) => i.id)).toEqual(['a']);
	});

	it('keeps the newer answer when an older one arrives after it', async () => {
		const older = deferred<QueueItem[]>();
		const newer = deferred<QueueItem[]>();
		const answers = [older.promise, newer.promise];
		const queue = new AddQueue(() => {}, server({ queue: () => answers.shift()! }));

		const first = queue.refresh();
		const second = queue.refresh();
		newer.resolve([item('a', 'TRANSCODING')]);
		await second;
		older.resolve([item('a', 'PENDING')]);
		await first;

		expect(queue.items[0].status).toBe('TRANSCODING');
	});

	it('reports when a video in progress leaves the queue, but not a failed one', async () => {
		const answers = [
			[item('working', 'DOWNLOADING'), item('failed', 'FAILED')],
			[item('working', 'DOWNLOADING')],
			[]
		];
		let ready = 0;
		const queue = new AddQueue(() => (ready += 1), server({ queue: async () => answers.shift()! }));

		await queue.refresh();
		await queue.refresh();
		expect(ready).toBe(0);

		await queue.refresh();
		expect(ready).toBe(1);
	});

	it('shows a failed send instead of staying busy when the server cannot be reached', async () => {
		const queue = new AddQueue(() => {}, server({ submit: noNetwork }));

		const results = await queue.send(['https://youtu.be/a']);

		expect(results).toBeNull();
		expect(queue.sendFailed).toBe(true);
		expect(queue.sending).toBe(false);
	});

	it('returns the result for each link and refreshes the queue', async () => {
		const result: SubmitResult = {
			url: 'https://youtu.be/a',
			result: 'queued',
			video_id: 'a',
			reason: null
		};
		const queue = new AddQueue(
			() => {},
			server({ submit: async () => [result], queue: async () => [item('a', 'PENDING')] })
		);

		const results = await queue.send(['https://youtu.be/a']);
		await Promise.resolve();

		expect(results).toEqual([result]);
		expect(queue.items.map((i) => i.id)).toEqual(['a']);
	});

	it('stops showing a retry as busy even when the server cannot be reached', async () => {
		const queue = new AddQueue(() => {}, server({ retry: noNetwork, queue: noNetwork }));

		await queue.retry('a');

		expect(queue.retrying.has('a')).toBe(false);
		expect(queue.loadFailed).toBe(true);
	});
});
