import { SvelteSet } from 'svelte/reactivity';
import { GUEST_USER_ID, api, type QueueItem, type SubmitResult } from '#lib/api/client.ts';
import { isWorking } from './status.ts';

export type QueueServer = {
	queue: () => Promise<QueueItem[]>;
	submit: (urls: string[]) => Promise<SubmitResult[]>;
	retry: (id: string) => Promise<void>;
};

const fromApi: QueueServer = {
	async queue() {
		const { data, error } = await api.GET('/videos/queue');
		if (error || !data) throw new Error('The server did not answer.');
		return data;
	},
	async submit(urls) {
		const { data, error } = await api.POST('/videos/batch', {
			body: { urls, user_id: GUEST_USER_ID, visibility: 'SHARED' }
		});
		if (error || !data) throw new Error('The server did not answer.');
		return data;
	},
	async retry(id) {
		// A 404 or 409 means the video changed meanwhile; the refresh that
		// follows shows how it is now.
		await api.POST('/videos/{video_id}/retry', { params: { path: { video_id: id } } });
	}
};

const POLL_MS = 3000;

// The Add page's side of the server: sending links, and the videos that are
// not ready yet, kept fresh by polling. A request that fails, with an error or
// with no network at all, shows as a failure, never as a stuck button.
export class AddQueue {
	items = $state<QueueItem[]>([]);
	loadFailed = $state(false);
	sending = $state(false);
	sendFailed = $state(false);
	retrying = new SvelteSet<string>();

	// Refreshes overlap (the poll, plus one after every send and retry) and
	// their answers can arrive out of order. Each is numbered, and only an
	// answer newer than the one on screen replaces it.
	#asked = 0;
	#shown = 0;
	#server: QueueServer;
	#onReady: () => void;

	constructor(onReady: () => void, server: QueueServer = fromApi) {
		this.#onReady = onReady;
		this.#server = server;
	}

	get workingCount(): number {
		return this.items.filter((item) => isWorking(item.status)).length;
	}

	get failedCount(): number {
		return this.items.filter((item) => item.status === 'FAILED').length;
	}

	// Refreshes now and then every few seconds while the tab is visible.
	// Returns the function that stops it.
	watch(): () => void {
		void this.refresh();
		const timer = setInterval(() => {
			if (!document.hidden) void this.refresh();
		}, POLL_MS);
		return () => clearInterval(timer);
	}

	async refresh(): Promise<void> {
		this.#asked += 1;
		const number = this.#asked;
		try {
			const items = await this.#server.queue();
			if (number <= this.#shown) return;
			this.#shown = number;
			this.loadFailed = false;
			// A video that was in progress and has left the queue is ready.
			const left = this.items.filter((item) => !items.some((next) => next.id === item.id));
			if (left.some((item) => isWorking(item.status))) this.#onReady();
			this.items = items;
		} catch {
			if (number <= this.#shown) return;
			this.#shown = number;
			this.loadFailed = true;
		}
	}

	// The result for each link, or null when the links could not be sent.
	async send(urls: string[]): Promise<SubmitResult[] | null> {
		this.sending = true;
		this.sendFailed = false;
		try {
			const results = await this.#server.submit(urls);
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
			await this.#server.retry(id);
		} catch {
			// No answer: the refresh below shows whether the server is reachable.
		}
		await this.refresh();
		this.retrying.delete(id);
	}
}
