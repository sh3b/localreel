import { afterEach, describe, expect, it, vi } from 'vitest';
import type { QueueItem, QueuePage, SubmitResult } from '#lib/api/client.ts';
import { AddQueue, type QueueServer } from './queue.svelte.ts';

function item(id: string, status: QueueItem['status']): QueueItem {
	return {
		id,
		status,
		source_url: `https://youtu.be/${id}`,
		error: status === 'FAILED' ? 'HTTP 403' : null,
		saved_at: '2026-11-01T00:00:00Z'
	};
}

// A queue answer whose totals count exactly the items, plus any waiting
// videos past the limit.
function page(items: QueueItem[], waitingNotShown = 0): QueuePage {
	const count = (status: QueueItem['status']) => items.filter((i) => i.status === status).length;
	return {
		items,
		totals: {
			pending: count('PENDING') + waitingNotShown,
			downloading: count('DOWNLOADING'),
			failed: count('FAILED')
		}
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
		queue: () => Promise.resolve(page([])),
		submit: () => Promise.resolve([]),
		retry: async () => {},
		remove: async () => {},
		...overrides
	};
}

const noNetwork = () => Promise.reject(new TypeError('Failed to fetch'));

// A server that never answers: the request only ends when it is given up.
function neverAnswered(signal: AbortSignal): Promise<never> {
	return new Promise((_, reject) => {
		signal.addEventListener('abort', () => reject(new Error('aborted')));
	});
}

describe('AddQueue', () => {
	afterEach(() => {
		vi.useRealTimers();
		vi.unstubAllGlobals();
	});

	it('polls while the tab is visible and skips while it is hidden', async () => {
		vi.useFakeTimers();
		const tab = Object.assign(new EventTarget(), { hidden: false });
		vi.stubGlobal('document', tab);
		let asked = 0;
		const queue = new AddQueue(
			server({
				queue: () => {
					asked += 1;
					return Promise.resolve(page([]));
				}
			})
		);

		const stop = queue.watch();
		await vi.advanceTimersByTimeAsync(3000);
		expect(asked).toBe(2);

		tab.hidden = true;
		await vi.advanceTimersByTimeAsync(9000);
		expect(asked).toBe(2);

		stop();
		tab.hidden = false;
		await vi.advanceTimersByTimeAsync(9000);
		expect(asked).toBe(2);
	});

	it('shows a failed load when the server cannot be reached, and clears it once it answers', async () => {
		let reachable = false;
		const queue = new AddQueue(
			server({ queue: async () => (reachable ? page([item('a', 'PENDING')]) : noNetwork()) })
		);

		await queue.refresh();
		expect(queue.loadFailed).toBe(true);

		reachable = true;
		await queue.refresh();
		expect(queue.loadFailed).toBe(false);
		expect(queue.items.map((i) => i.id)).toEqual(['a']);
	});

	it('keeps the newer answer when an older one arrives after it', async () => {
		const older = deferred<QueuePage>();
		const newer = deferred<QueuePage>();
		const answers = [older.promise, newer.promise];
		const queue = new AddQueue(server({ queue: () => answers.shift()! }));

		const first = queue.refresh();
		const second = queue.refresh();
		newer.resolve(page([item('a', 'DOWNLOADING')]));
		await second;
		older.resolve(page([item('a', 'PENDING')]));
		await first;

		expect(queue.items[0].status).toBe('DOWNLOADING');
	});

	it('refreshes as soon as the tab is shown again', async () => {
		vi.useFakeTimers();
		const tab = Object.assign(new EventTarget(), { hidden: true });
		vi.stubGlobal('document', tab);
		let asked = 0;
		const queue = new AddQueue(
			server({
				queue: () => {
					asked += 1;
					return Promise.resolve(page([]));
				}
			})
		);
		const stop = queue.watch();
		await vi.advanceTimersByTimeAsync(0);

		tab.hidden = false;
		tab.dispatchEvent(new Event('visibilitychange'));
		await vi.advanceTimersByTimeAsync(0);

		expect(asked).toBe(2);
		stop();
	});

	it('skips a poll while the last refresh is still unanswered', async () => {
		vi.useFakeTimers();
		vi.stubGlobal('document', Object.assign(new EventTarget(), { hidden: false }));
		const answer = deferred<QueuePage>();
		let asked = 0;
		const queue = new AddQueue(
			server({
				queue: () => {
					asked += 1;
					return answer.promise;
				}
			})
		);

		const stop = queue.watch();
		await vi.advanceTimersByTimeAsync(9000);
		expect(asked).toBe(1);

		answer.resolve(page([]));
		await vi.advanceTimersByTimeAsync(3000);
		expect(asked).toBe(2);
		stop();
	});

	it('gives up on a refresh the server never answers, and keeps polling', async () => {
		vi.useFakeTimers();
		vi.stubGlobal('document', Object.assign(new EventTarget(), { hidden: false }));
		let asked = 0;
		const queue = new AddQueue(
			server({
				queue: (signal) => {
					asked += 1;
					return neverAnswered(signal);
				}
			})
		);

		const stop = queue.watch();
		await vi.advanceTimersByTimeAsync(10_000);
		expect(queue.loadFailed).toBe(true);

		await vi.advanceTimersByTimeAsync(3000);
		expect(asked).toBe(2);
		stop();
	});

	it('gives up on a send, retry or remove the server never answers', async () => {
		vi.useFakeTimers();
		const queue = new AddQueue(
			server({
				submit: (_urls, signal) => neverAnswered(signal),
				retry: (_id, signal) => neverAnswered(signal),
				remove: (_id, signal) => neverAnswered(signal)
			})
		);

		const sent = queue.send(['https://youtu.be/a']);
		void queue.retry('a');
		void queue.remove('b');
		await vi.advanceTimersByTimeAsync(10_000);

		expect(await sent).toBeNull();
		expect([queue.sending, queue.sendFailed]).toEqual([false, true]);
		expect([queue.retrying.has('a'), queue.removing.has('b')]).toEqual([false, false]);
	});

	it('counts the waiting videos past the limit', async () => {
		const queue = new AddQueue(
			server({
				queue: () =>
					Promise.resolve(
						page([item('a', 'DOWNLOADING'), item('b', 'FAILED'), item('c', 'PENDING')], 5)
					)
			})
		);

		await queue.refresh();

		expect(queue.totals).toEqual({ pending: 6, downloading: 1, failed: 1 });
		expect(queue.waitingNotShown).toBe(5);
	});

	it('shows a failed send instead of staying busy when the server cannot be reached', async () => {
		const queue = new AddQueue(server({ submit: noNetwork }));

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
			server({
				submit: () => Promise.resolve([result]),
				queue: () => Promise.resolve(page([item('a', 'PENDING')]))
			})
		);

		const results = await queue.send(['https://youtu.be/a']);
		await Promise.resolve();

		expect(results).toEqual([result]);
		expect(queue.items.map((i) => i.id)).toEqual(['a']);
	});

	it('stops showing a retry as busy even when the server cannot be reached', async () => {
		const queue = new AddQueue(server({ retry: noNetwork, queue: noNetwork }));

		await queue.retry('a');

		expect(queue.retrying.has('a')).toBe(false);
		expect(queue.loadFailed).toBe(true);
	});

	it('removes a video and shows the queue without it', async () => {
		let ids = ['a', 'b'];
		const queue = new AddQueue(
			server({
				remove: (id) => {
					ids = ids.filter((other) => other !== id);
					return Promise.resolve();
				},
				queue: () => Promise.resolve(page(ids.map((id) => item(id, 'PENDING'))))
			})
		);
		await queue.refresh();

		await queue.remove('a');

		expect(queue.items.map((i) => i.id)).toEqual(['b']);
		expect(queue.removing.has('a')).toBe(false);
	});

	it('stops showing a remove as busy even when the server cannot be reached', async () => {
		const queue = new AddQueue(server({ remove: noNetwork, queue: noNetwork }));

		await queue.remove('a');

		expect(queue.removing.has('a')).toBe(false);
		expect(queue.loadFailed).toBe(true);
	});
});
