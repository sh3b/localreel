import { api, type VideoCard, type VideoPage, type VideoSort } from '#lib/api/client.ts';
import { withTimeout } from '#lib/api/timeout.ts';

export type PageRequest = { sort: VideoSort; after: string | null; limit: number };

export type StreamServer = {
	page: (request: PageRequest, signal: AbortSignal) => Promise<VideoPage>;
	remove: (id: string, signal: AbortSignal) => Promise<void>;
};

const PAGE_SIZE = 24;

const fromApi: StreamServer = {
	async page({ sort, after, limit }, signal) {
		const { data, error } = await api.GET('/videos', {
			params: { query: { sort, after, limit } },
			signal
		});
		if (error || !data) throw new Error('The server did not answer.');
		return data;
	},
	async remove(id, signal) {
		const { error, response } = await api.DELETE('/videos/{video_id}', {
			params: { path: { video_id: id } },
			signal
		});
		// 404: someone removed it already, which is what was asked.
		if (error && response.status !== 404) throw new Error('The server did not remove it.');
	}
};

// The ready videos in the chosen order, and where the Feed is in them. One
// shared instance, `stream`, so the Feed keeps its place when it is left and
// opened again.
export class VideoStream {
	items = $state<VideoCard[]>([]);
	sort = $state<VideoSort>('newest');
	position = $state(0);
	complete = $state(false);
	loading = $state(false);
	loadFailed = $state(false);
	removing = $state(false);
	removeFailed = $state(false);

	#cursor: string | null = null;
	#started = false;
	// Bumped by every restart. A page only lands in the list if no restart
	// happened while it loaded; otherwise it belongs to the old list.
	#generation = 0;
	// The load in flight, so a second caller can wait for it instead of
	// returning before the page is in.
	#pending: Promise<void> = Promise.resolve();
	#server: StreamServer;

	constructor(server: StreamServer = fromApi) {
		this.#server = server;
	}

	get current(): VideoCard | undefined {
		return this.items[this.position];
	}

	get next(): VideoCard | undefined {
		return this.items[this.position + 1];
	}

	get atEnd(): boolean {
		return this.complete && this.position >= this.items.length - 1;
	}

	async ensureLoaded(): Promise<void> {
		if (!this.#started) await this.restart(this.sort);
	}

	async restart(sort: VideoSort): Promise<void> {
		this.#started = true;
		this.#generation += 1;
		this.sort = sort;
		this.items = [];
		this.position = 0;
		this.complete = false;
		this.loading = false;
		this.loadFailed = false;
		this.#cursor = null;
		await this.loadMore();
	}

	// Loads the first page again, to show videos that became ready since. The
	// list stays on screen until the new page is in, and the Feed stays on its
	// video if that one is in the new page; otherwise it starts at the top.
	refresh(): Promise<void> {
		if (!this.#started) return this.restart(this.sort);
		this.#generation += 1;
		this.#pending = this.#load(true);
		return this.#pending;
	}

	loadMore(): Promise<void> {
		if (this.complete) return Promise.resolve();
		if (!this.loading) this.#pending = this.#load(false);
		return this.#pending;
	}

	async #load(fromTop: boolean): Promise<void> {
		const generation = this.#generation;
		const request = { sort: this.sort, after: fromTop ? null : this.#cursor, limit: PAGE_SIZE };
		this.loading = true;
		this.loadFailed = false;
		try {
			const page = await withTimeout((signal) => this.#server.page(request, signal));
			if (generation !== this.#generation) return;
			if (fromTop) {
				// Read now, not before the request: a tile opened meanwhile counts.
				const shown = this.current?.id;
				this.items = page.items;
				this.position = Math.max(
					0,
					page.items.findIndex((video) => video.id === shown)
				);
			} else {
				this.items = [...this.items, ...page.items];
			}
			this.#cursor = page.next_cursor;
			this.complete = page.next_cursor === null;
		} catch {
			if (generation !== this.#generation) return;
			this.loadFailed = true;
		} finally {
			if (generation === this.#generation) this.loading = false;
		}
	}

	// Removes the video for good. The list keeps showing the same video, or
	// the one after it if this was the one shown.
	async remove(id: string): Promise<void> {
		this.removing = true;
		this.removeFailed = false;
		try {
			await withTimeout((signal) => this.#server.remove(id, signal));
		} catch {
			this.removeFailed = true;
			return;
		} finally {
			this.removing = false;
		}
		const index = this.items.findIndex((video) => video.id === id);
		if (index === -1) return;
		this.items = this.items.filter((video) => video.id !== id);
		if (index < this.position) this.position -= 1;
		// Clamps the position, and loads more if the list got short.
		await this.go(this.position);
	}

	// Moves the feed, and loads the next page well before it is needed.
	async go(index: number): Promise<void> {
		this.position = this.#clamp(index);
		if (this.items.length - this.position > 3) return;
		const before = this.position;
		await this.loadMore();
		// Asked to move past the last loaded video (its page failed or is still
		// loading): finish the move now that the page is in, unless the feed
		// moved meanwhile.
		if (this.position === before) this.position = this.#clamp(index);
	}

	async step(delta: 1 | -1): Promise<void> {
		await this.go(this.position + delta);
	}

	#clamp(index: number): number {
		return Math.max(0, Math.min(index, this.items.length - 1));
	}
}

export const stream = new VideoStream();
