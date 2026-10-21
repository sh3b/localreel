import { api, type VideoCard, type VideoPage, type VideoSort } from '#lib/api/client.ts';

export type PageRequest = { sort: VideoSort; after: string | null; limit: number };
export type PageLoader = (request: PageRequest) => Promise<VideoPage>;

const PAGE_SIZE = 24;

async function loadFromApi({ sort, after, limit }: PageRequest): Promise<VideoPage> {
	const { data, error } = await api.GET('/videos', {
		params: { query: { sort, limit, ...(after ? { after } : {}) } }
	});
	if (error || !data) throw new Error('The server did not answer.');
	return data;
}

// The list of ready videos in the chosen order. The Feed and the Library read
// the same instance, so opening a video from the Library continues the Feed in
// exactly the same order.
export class VideoStream {
	items = $state<VideoCard[]>([]);
	sort = $state<VideoSort>('newest');
	position = $state(0);
	complete = $state(false);
	loading = $state(false);
	error = $state<string | null>(null);

	#cursor: string | null = null;
	#started = false;
	#loadPage: PageLoader;

	constructor(loadPage: PageLoader = loadFromApi) {
		this.#loadPage = loadPage;
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
		this.sort = sort;
		this.items = [];
		this.position = 0;
		this.complete = false;
		this.#cursor = null;
		await this.loadMore();
	}

	async loadMore(): Promise<void> {
		if (this.loading || this.complete) return;
		this.loading = true;
		this.error = null;
		const sort = this.sort;
		try {
			const page = await this.#loadPage({ sort, after: this.#cursor, limit: PAGE_SIZE });
			// A restart with another order may have happened while this page loaded.
			if (sort !== this.sort) return;
			this.items = [...this.items, ...page.items];
			this.#cursor = page.next_cursor;
			this.complete = page.next_cursor === null;
		} catch (error) {
			this.error = error instanceof Error ? error.message : String(error);
		} finally {
			this.loading = false;
		}
	}

	// Moves the feed and starts loading the next page well before it is needed.
	async go(index: number): Promise<void> {
		this.position = Math.max(0, Math.min(index, this.items.length - 1));
		if (this.items.length - this.position <= 3) await this.loadMore();
	}

	async step(delta: 1 | -1): Promise<void> {
		await this.go(this.position + delta);
	}
}

export const stream = new VideoStream();
