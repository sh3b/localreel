<script lang="ts">
	import { onMount, tick } from 'svelte';
	import type { VideoCard, VideoSort } from '#lib/api/client.ts';
	import { controlButton, primaryButton } from '#lib/components/buttons.ts';
	import SortSwitch from '#lib/components/library/SortSwitch.svelte';
	import TileContent from '#lib/components/library/TileContent.svelte';
	import RemoveVideoDialog from '#lib/components/RemoveVideoDialog.svelte';
	import StatePanel from '#lib/components/StatePanel.svelte';
	import { isTyping } from '#lib/shell/keyboard.ts';
	import { shell } from '#lib/shell/shell.svelte.ts';
	import { titleOf } from '#lib/videos/format.ts';
	import { gridMove } from '#lib/videos/grid.ts';
	import { stream } from '#lib/videos/stream.svelte.ts';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';

	let focused = $state(0);
	let grid = $state<HTMLElement>();
	let scroller = $state<HTMLElement>();
	let sentinel = $state<HTMLElement>();
	const tiles: HTMLElement[] = [];
	// The video waiting for "remove" to be confirmed.
	let confirming = $state<VideoCard | null>(null);

	onMount(() => {
		shell.hints = [
			{ keys: 'arrows', action: 'move' },
			{ keys: 'enter', action: 'open in feed' },
			{ keys: 's', action: 'change order' },
			{ keys: 'x', action: 'remove' }
		];
		void stream.refresh().then(async () => {
			// Read after loading: a reload resets the position, and a stale one
			// would leave no tile reachable by keyboard.
			focused = stream.position;
			await tick();
			// Coming back from the Feed lands on the video that was playing.
			tiles[focused]?.scrollIntoView({ block: 'center' });
		});
		return () => {
			shell.hints = [];
			shell.status = '';
		};
	});

	$effect(() => {
		const count = stream.items.length;
		shell.status = count > 0 ? `${count}${stream.complete ? '' : '+'} videos ${stream.sort}` : '';
	});

	// Load the next page while the end of the grid is within 600px of view.
	// The margin is measured from the scrolling box, not the window, or it would
	// never apply. The observer is rebuilt after every page because it only
	// reports changes: on a screen tall enough to show every tile so far, the
	// end never comes back into view, and loading would stop.
	$effect(() => {
		void stream.items.length;
		if (!sentinel || !scroller) return;
		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting)) void stream.loadMore();
			},
			{ root: scroller, rootMargin: '600px' }
		);
		observer.observe(sentinel);
		return () => observer.disconnect();
	});

	function open(index: number) {
		void stream.go(index);
		void goto(resolve('/'));
	}

	function changeOrder(sort: VideoSort) {
		focused = 0;
		void stream.restart(sort);
	}

	async function removeConfirmed(id: string) {
		confirming = null;
		await stream.remove(id);
		// Stay on the tile that moved into this place, or the last one.
		focused = Math.max(0, Math.min(focused, stream.items.length - 1));
		await tick();
		tiles[focused]?.focus();
	}

	function columns(): number {
		if (!grid) return 1;
		return getComputedStyle(grid).gridTemplateColumns.split(' ').length;
	}

	function onkeydown(event: KeyboardEvent) {
		// The dialog handles its own keys; the grid must not move under it.
		if (confirming) return;
		if (isTyping(event) || event.metaKey || event.ctrlKey || event.altKey) return;
		if (event.key === 's') {
			event.preventDefault();
			changeOrder(stream.sort === 'newest' ? 'oldest' : 'newest');
			return;
		}
		if (!grid?.contains(document.activeElement)) {
			// The first arrow press moves into the grid.
			if (event.key.startsWith('Arrow') && stream.items.length > 0) {
				event.preventDefault();
				tiles[focused]?.focus();
			}
			return;
		}
		if (event.key === 'x') {
			event.preventDefault();
			confirming = stream.items[focused] ?? null;
			return;
		}
		const cols = columns();
		const target = gridMove(focused, event.key, cols, stream.items.length);
		if (target === null) return;
		event.preventDefault();
		focused = target;
		tiles[target]?.focus();
		tiles[target]?.scrollIntoView({ block: 'nearest' });
		if (stream.items.length - target <= cols * 2) void stream.loadMore();
	}
</script>

<svelte:window {onkeydown} />

<div class="flex h-full flex-col">
	<div class="flex h-bar shrink-0 items-center gap-3 border-b border-line px-4">
		<span class="text-accent" aria-hidden="true">&gt;</span>
		<span class="text-faint">sort:</span>
		<SortSwitch value={stream.sort} onchange={changeOrder} />
		{#if stream.removeFailed}
			<p class="ml-auto truncate text-danger">The video could not be removed; try again.</p>
		{/if}
	</div>

	<div bind:this={scroller} class="min-h-0 flex-1 overflow-y-auto">
		{#if stream.items.length === 0}
			{#if stream.loadFailed}
				<StatePanel title="The library could not be loaded.">
					The server did not answer. Check that it is running.
					{#snippet actions()}
						<button type="button" class={primaryButton} onclick={() => stream.restart(stream.sort)}>
							try again
						</button>
					{/snippet}
				</StatePanel>
			{:else if stream.complete}
				<StatePanel title="Your library is empty.">
					Videos you add show up here once they are ready to play.
					{#snippet actions()}
						<a href={resolve('/add')} class={primaryButton}><kbd>3</kbd> add videos</a>
					{/snippet}
				</StatePanel>
			{:else}
				<p class="flex h-full items-center justify-center text-faint">Loading the library…</p>
			{/if}
		{:else}
			<ul
				bind:this={grid}
				aria-label="Videos"
				class="grid grid-cols-[repeat(auto-fill,minmax(6.5rem,1fr))] gap-3 p-3 md:grid-cols-[repeat(auto-fill,minmax(9.5rem,1fr))] md:gap-tile md:p-4"
			>
				{#each stream.items as video, index (video.id)}
					<li class="flex flex-col gap-1">
						<button
							bind:this={tiles[index]}
							type="button"
							tabindex={index === focused ? 0 : -1}
							onclick={() => open(index)}
							onfocus={() => (focused = index)}
							aria-label="Play {titleOf(video.title)} in the feed"
							class="block w-full outline-offset-2"
						>
							<TileContent {video} />
						</button>
						<!-- Out of the tab order: the grid is one stop, and x removes the focused tile. -->
						<button
							type="button"
							tabindex="-1"
							disabled={stream.removing}
							onclick={() => (confirming = video)}
							aria-label="Remove {titleOf(video.title)}"
							class="min-h-6 self-end px-1 text-caption text-faint hover:text-danger disabled:cursor-not-allowed disabled:opacity-50"
						>
							remove
						</button>
					</li>
				{/each}
			</ul>
			<div bind:this={sentinel} class="h-px" aria-hidden="true"></div>
			{#if stream.loading}
				<p class="pb-6 text-center text-faint">Loading more…</p>
			{:else if stream.loadFailed}
				<p class="pb-6 text-center text-danger">
					The next videos could not be loaded.
					<button type="button" class={controlButton} onclick={() => stream.loadMore()}>
						try again
					</button>
				</p>
			{/if}
		{/if}
	</div>
</div>

{#if confirming}
	<RemoveVideoDialog
		video={confirming}
		onconfirm={() => confirming && removeConfirmed(confirming.id)}
		oncancel={() => (confirming = null)}
	/>
{/if}
