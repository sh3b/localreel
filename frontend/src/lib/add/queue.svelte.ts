import { SvelteSet } from 'svelte/reactivity';
import { api, type QueuePage, type SubmitResult } from '#lib/api/client.ts';
import { withTimeout } from '#lib/api/timeout.ts';

export type QueueServer = {
	queue: (signal: AbortSignal) => Promise<QueuePage>;
	submit: (urls: string[], signal: AbortSignal) => Promise<SubmitResult[]>;
	retry: (id: string, signal: AbortSignal) => Promise<void>;
	remove: (id: string, signal: AbortSignal) => Promise<void>;
};

// The largest limit GET /videos/queue accepts (routers/videos.py). The server
// lists downloading and failed videos first, so only waiting ones are cut off.
const QUEUE_LIMIT = 100;

const fromApi: QueueServer = {
	async queue(signal) {
		const { data, error } = await api.GET('/videos/queue', {
			params: { query: { limit: QUEUE_LIMIT } },
			signal
		});
		if (error || !data) throw new Error('The server did not answer.');
		return data;
	},
	async submit(urls, signal) {
		const { data, error } = await api.POST('/videos/batch', { body: { urls }, signal });
		if (error || !data) throw new Error('The server did not answer.');
		return data;
	},
	async retry(id, signal) {
		// A 404 or 409 means the video changed meanwhile; the refresh that
		// follows shows how it is now.
		await api.POST('/videos/{video_id}/retry', {
			params: { path: { video_id: id } },
			signal
		});
	},
	async remove(id, signal) {
		// Same as retry: a 404 or 409 shows in the refresh that follows.
		await api.DELETE('/videos/{video_id}', { params: { path: { video_id: id } }, signal });
	}
};

// Polls wait for the last refresh, so one the server never answered would
// stop them; withTimeout gives every request up after a while.
const POLL_MS = 3000;

// The Add page's side of the server: sending links, and the videos that are
// not ready yet, kept fresh by polling. A request that fails, with an error or
// with no network at all, shows as a failure, never as a stuck button.
export class AddQueue {
	items = $state<QueuePage['items']>([]);
	totals = $state<QueuePage['totals']>({ pending: 0, downloading: 0, failed: 0 });
	loadFailed = $state(false);
	sending = $state(false);
	sendFailed = $state(false);
	retrying = new SvelteSet<string>();
	removing = new SvelteSet<string>();

	// Refreshes overlap (the poll, plus one after every send, retry and remove) and
	// their answers can arrive out of order. Each is numbered, and only an
	// answer newer than the one on screen replaces it.
	#asked = 0;
	#shown = 0;
	#loading = 0;
	#server: QueueServer;

	constructor(server: QueueServer = fromApi) {
		this.#server = server;
	}

	// Waiting videos past the limit: in the totals but not in the list.
	get waitingNotShown(): number {
		const shown = this.items.filter((item) => item.status === 'PENDING').length;
		return this.totals.pending - shown;
	}

	// Refreshes now, every few seconds while the tab is visible, and as soon
	// as the tab is shown again. Returns the function that stops it.
	watch(): () => void {
		const refreshIfSeen = () => {
			// A slow server would otherwise collect a pile of unanswered polls.
			if (!document.hidden && this.#loading === 0) void this.refresh();
		};
		void this.refresh();
		const timer = setInterval(refreshIfSeen, POLL_MS);
		document.addEventListener('visibilitychange', refreshIfSeen);
		return () => {
			clearInterval(timer);
			document.removeEventListener('visibilitychange', refreshIfSeen);
		};
	}

	async refresh(): Promise<void> {
		this.#asked += 1;
		const number = this.#asked;
		this.#loading += 1;
		try {
			const queue = await withTimeout((signal) => this.#server.queue(signal));
			if (number <= this.#shown) return;
			this.#shown = number;
			this.loadFailed = false;
			this.items = queue.items;
			this.totals = queue.totals;
		} catch {
			if (number <= this.#shown) return;
			this.#shown = number;
			this.loadFailed = true;
		} finally {
			this.#loading -= 1;
		}
	}

	// The result for each link, or null when the links could not be sent.
	async send(urls: string[]): Promise<SubmitResult[] | null> {
		this.sending = true;
		this.sendFailed = false;
		try {
			const results = await withTimeout((signal) => this.#server.submit(urls, signal));
			void this.refresh();
			return results;
		} catch {
			this.sendFailed = true;
			return null;
		} finally {
			this.sending = false;
		}
	}

	async retry(id: string): Promise<void> {
		this.retrying.add(id);
		try {
			await withTimeout((signal) => this.#server.retry(id, signal));
		} catch {
			// No answer: the refresh below shows whether the server is reachable.
		}
		await this.refresh();
		this.retrying.delete(id);
	}

	async remove(id: string): Promise<void> {
		this.removing.add(id);
		try {
			await withTimeout((signal) => this.#server.remove(id, signal));
		} catch {
			// No answer: the refresh below shows whether the server is reachable.
		}
		await this.refresh();
		this.removing.delete(id);
	}
}
