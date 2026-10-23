import { api, type VideoCard, type VideoPage, type VideoSort } from '#lib/api/client.ts';

export type PageRequest = { sort: VideoSort; after: string | null; limit: number };
export type PageLoader = (request: PageRequest, signal: AbortSignal) => Promise<VideoPage>;

const PAGE_SIZE = 24;

async function loadFromApi(
	{ sort, after, limit }: PageRequest,
	signal: AbortSignal
): Promise<VideoPage> {
	const { data, error } = await api.GET('/videos', {
		params: { query: { sort, limit, ...(after ? { after } : {}) } },
		signal
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
	// Bumped by every restart. A page only lands in the list if no restart
	// happened while it loaded; otherwise it belongs to the old list.
	#generation = 0;
	#request: AbortController | null = null;
	// The load in flight, so a second caller can wait for it instead of
	// returning before the page is in.
	#pending: Promise<void> = Promise.resolve();
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

	// New videos became ready elsewhere (the Add page): load afresh next time
	// the Feed or the Library opens, keeping the chosen order.
	invalidate(): void {
		this.#started = false;
	}

	async restart(sort: VideoSort): Promise<void> {
		this.#started = true;
		this.#generation += 1;
		this.#request?.abort();
		this.sort = sort;
		this.items = [];
		this.position = 0;
		this.complete = false;
		this.loading = false;
		this.error = null;
		this.#cursor = null;
		await this.loadMore();
	}

	loadMore(): Promise<void> {
		if (this.complete) return Promise.resolve();
		if (!this.loading) this.#pending = this.#load();
		return this.#pending;
	}

	async #load(): Promise<void> {
		const generation = this.#generation;
		const request = new AbortController();
		this.#request = request;
		this.loading = true;
		this.error = null;
		try {
			const page = await this.#loadPage(
				{ sort: this.sort, after: this.#cursor, limit: PAGE_SIZE },
				request.signal
			);
			if (generation !== this.#generation) return;
			this.items = [...this.items, ...page.items];
			this.#cursor = page.next_cursor;
			this.complete = page.next_cursor === null;
		} catch (error) {
			// A restart cancelled this request; that is not an error to show.
			if (generation !== this.#generation) return;
			this.error = error instanceof Error ? error.message : String(error);
		} finally {
			if (generation === this.#generation) this.loading = false;
		}
	}

	// Moves the feed and starts loading the next page well before it is needed.
	async go(index: number): Promise<void> {
		this.position = this.#clamp(index);
		if (this.items.length - this.position > 3) return;
		const before = this.position;
		await this.loadMore();
		// Asked to move past the last loaded video (the earlier load failed or is
		// still running): finish the move now that the page is in, unless the feed moved meanwhile.
		if (this.position === before) this.position = this.#clamp(index);
	}

	#clamp(index: number): number {
		return Math.max(0, Math.min(index, this.items.length - 1));
	}

	async step(delta: 1 | -1): Promise<void> {
		await this.go(this.position + delta);
	}
}

export const stream = new VideoStream();
