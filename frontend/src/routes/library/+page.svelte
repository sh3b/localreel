<script lang="ts">
	import { onMount, tick } from 'svelte';
	import type { VideoSort } from '#lib/api/client.ts';
	import { primaryButton } from '#lib/components/buttons.ts';
	import SortSwitch from '#lib/components/library/SortSwitch.svelte';
	import TileContent from '#lib/components/library/TileContent.svelte';
	import StatePanel from '#lib/components/StatePanel.svelte';
	import { isTyping, shell } from '#lib/shell/shell.svelte.ts';
	import { gridMove } from '#lib/videos/grid.ts';
	import { stream } from '#lib/videos/stream.svelte.ts';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';

	let focused = $state(0);
	let grid = $state<HTMLElement>();
	let scroller = $state<HTMLElement>();
	let sentinel = $state<HTMLElement>();
	const tiles: HTMLElement[] = [];

	onMount(() => {
		shell.hints = [
			{ keys: 'arrows', action: 'move' },
			{ keys: 'enter', action: 'open in feed' },
			{ keys: 's', action: 'change order' }
		];
		void stream.ensureLoaded().then(async () => {
			// Read after loading: a reload resets the position, and a stale one
			// would leave no tile reachable by keyboard.
			focused = stream.position;
			await tick();
			// Coming back from the Feed lands on the video that was playing.
			tiles[focused]?.scrollIntoView({ block: 'center' });
		});
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

	function columns(): number {
		if (!grid) return 1;
		return getComputedStyle(grid).gridTemplateColumns.split(' ').length;
	}

	function onkeydown(event: KeyboardEvent) {
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
	</div>

	<div bind:this={scroller} class="min-h-0 flex-1 overflow-y-auto">
		{#if stream.items.length === 0}
			{#if stream.error}
				<StatePanel title="The library could not be loaded.">
					{stream.error} Check that the localreel containers are running.
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
					<li>
						<button
							bind:this={tiles[index]}
							type="button"
							tabindex={index === focused ? 0 : -1}
							onclick={() => open(index)}
							onfocus={() => (focused = index)}
							aria-label="Play {video.title ?? 'video'} in the feed"
							class="block w-full outline-offset-2"
						>
							<TileContent {video} />
						</button>
					</li>
				{/each}
			</ul>
			<div bind:this={sentinel} class="h-px" aria-hidden="true"></div>
			{#if stream.loading}
				<p class="pb-6 text-center text-faint">Loading more…</p>
			{:else if stream.error}
				<p class="pb-6 text-center text-danger">
					{stream.error}
					<button type="button" class="underline" onclick={() => stream.loadMore()}
						>try again</button
					>
				</p>
			{/if}
		{/if}
	</div>
</div>
