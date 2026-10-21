<script lang="ts">
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import StatePanel from '#lib/components/StatePanel.svelte';
	import { primaryButton, secondaryButton } from '#lib/components/buttons.ts';
	import FeedVideo from '#lib/components/feed/FeedVideo.svelte';
	import Filmstrip from '#lib/components/feed/Filmstrip.svelte';
	import PlayerControls from '#lib/components/feed/PlayerControls.svelte';
	import VideoDetails from '#lib/components/feed/VideoDetails.svelte';
	import { isTyping, shell } from '#lib/shell/shell.svelte.ts';
	import { formatDuration, formatPosition, shapeOf } from '#lib/videos/format.ts';
	import { readSoundOn, saveSoundOn } from '#lib/videos/sound.ts';
	import { stream } from '#lib/videos/stream.svelte.ts';

	let muted = $state(true);
	let paused = $state(false);
	let finished = $state(false);
	let fullscreen = $state(false);
	let controlsVisible = $state(true);
	let stage = $state<HTMLElement>();
	let hideTimer: ReturnType<typeof setTimeout> | undefined;

	const video = $derived(stream.current);
	const shape = $derived(video ? shapeOf(video.width, video.height) : 'portrait');
	const position = $derived(formatPosition(stream.position, stream.items.length, stream.complete));

	onMount(() => {
		muted = !readSoundOn();
		shell.hints = [
			{ keys: 'j k', action: 'next / previous' },
			{ keys: 'space', action: 'play / pause' },
			{ keys: 'f', action: 'fullscreen' },
			{ keys: 'm', action: 'sound' }
		];
		void stream.ensureLoaded();
		return () => clearTimeout(hideTimer);
	});

	$effect(() => {
		shell.status = stream.items.length > 0 ? `${position} ${stream.sort}` : '';
	});

	async function next() {
		if (stream.atEnd) {
			finished = true;
			return;
		}
		await stream.step(1);
	}

	async function previous() {
		if (finished) {
			finished = false;
			return;
		}
		await stream.step(-1);
	}

	function startOver() {
		finished = false;
		void stream.go(0);
	}

	function togglePlay() {
		paused = !paused;
	}

	function toggleSound() {
		muted = !muted;
		saveSoundOn(!muted);
	}

	function toggleFullscreen() {
		if (document.fullscreenElement) void document.exitFullscreen();
		else void stage?.requestFullscreen();
	}

	// In fullscreen the details fade out while playing and come back on input.
	function wake() {
		controlsVisible = true;
		clearTimeout(hideTimer);
		hideTimer = setTimeout(() => (controlsVisible = false), 2500);
	}

	function onkeydown(event: KeyboardEvent) {
		if (isTyping(event) || event.metaKey || event.ctrlKey || event.altKey) return;
		const actions: Record<string, () => void> = {
			j: next,
			ArrowDown: next,
			k: previous,
			ArrowUp: previous,
			' ': togglePlay,
			f: toggleFullscreen,
			m: toggleSound,
			g: () => finished && startOver()
		};
		const action = actions[event.key];
		if (!action || stream.items.length === 0) return;
		event.preventDefault();
		action();
		if (fullscreen) wake();
	}

	let lastWheel = 0;
	function onwheel(event: WheelEvent) {
		if (Math.abs(event.deltaY) < 30) return;
		const now = performance.now();
		if (now - lastWheel < 700) return;
		lastWheel = now;
		void (event.deltaY > 0 ? next() : previous());
	}

	let touchStartY: number | null = null;
	function ontouchstart(event: TouchEvent) {
		touchStartY = event.touches[0].clientY;
	}
	function ontouchend(event: TouchEvent) {
		if (touchStartY === null) return;
		const distance = touchStartY - event.changedTouches[0].clientY;
		touchStartY = null;
		if (Math.abs(distance) > 60) void (distance > 0 ? next() : previous());
	}

	function onfullscreenchange() {
		fullscreen = document.fullscreenElement === stage;
		if (fullscreen) wake();
	}
</script>

<svelte:window {onkeydown} />
<svelte:document {onfullscreenchange} />

{#if stream.items.length === 0}
	{#if stream.error}
		<StatePanel marker="00/00" title="The videos could not be loaded.">
			{stream.error} Check that the localreel containers are running.
			{#snippet actions()}
				<button type="button" class={primaryButton} onclick={() => stream.restart(stream.sort)}>
					try again
				</button>
			{/snippet}
		</StatePanel>
	{:else if stream.complete}
		<StatePanel
			marker="00/00"
			title="Nothing here yet. Paste a link and it will be kept on your own disk."
		>
			Videos show up here once they are downloaded and ready to play.
			{#snippet actions()}
				<a href={resolve('/add')} class={primaryButton}><kbd>3</kbd> add videos</a>
			{/snippet}
		</StatePanel>
	{:else}
		<p class="flex h-full items-center justify-center text-faint">Loading videos…</p>
	{/if}
{:else if finished}
	<StatePanel marker={position} title="You're all caught up.">
		That was the last of {stream.items.length} videos. Nothing repeats until you start again.
		{#snippet actions()}
			<button type="button" class={primaryButton} onclick={startOver}>
				<kbd>g</kbd> back to the start
			</button>
			<a href={resolve('/library')} class={secondaryButton}><kbd>2</kbd> library</a>
		{/snippet}
	</StatePanel>
{:else if video}
	<div class="flex h-full">
		<div
			bind:this={stage}
			class={[
				'relative flex min-h-0 min-w-0 flex-1 overflow-hidden',
				fullscreen ? 'bg-media' : 'bg-bg'
			]}
			role="region"
			aria-label="Feed"
			{onwheel}
			{ontouchstart}
			{ontouchend}
			onmousemove={fullscreen ? wake : undefined}
		>
			<div
				class={[
					'flex h-full w-full items-center justify-center',
					!fullscreen && 'md:gap-16 md:p-6',
					!fullscreen && shape === 'landscape' && 'md:flex-col md:gap-6'
				]}
			>
				<div
					class={[
						'relative h-full w-full',
						// Portrait and square: as tall as the stage, width from the ratio.
						// Landscape: takes the height left above the details and
						// letterboxes inside it, so the column never overflows.
						!fullscreen &&
							(shape === 'landscape'
								? 'md:aspect-(--ratio) md:min-h-0 md:w-auto md:max-w-full md:flex-1'
								: 'md:aspect-(--ratio) md:w-auto md:max-w-[60%]')
					]}
					style:--ratio="{video.width ?? 9} / {video.height ?? 16}"
				>
					{#key video.id}
						<FeedVideo {video} bind:muted bind:paused onended={next} />
					{/key}

					<!-- On phones, and in fullscreen, the details sit over the picture. -->
					<div
						class={[
							'pointer-events-none absolute inset-x-0 bottom-0 flex flex-col gap-2.5 bg-gradient-to-t from-black/90 to-transparent p-4 pt-24 text-white transition-opacity',
							fullscreen ? !(controlsVisible || paused) && 'opacity-0' : 'md:hidden'
						]}
					>
						<p class="text-accent">{position}</p>
						<p class="font-title text-lg leading-snug font-medium">
							{video.title ?? 'Untitled video'}
						</p>
						<p class="text-white/75">
							{[video.uploader, formatDuration(video.duration_sec)].filter(Boolean).join(', ')}
						</p>
						{#if video.tags.length > 0}
							<p class="text-accent">{video.tags.map((tag) => `#${tag}`).join(' ')}</p>
						{/if}
						<div class="pointer-events-auto">
							<PlayerControls
								{paused}
								{muted}
								{fullscreen}
								onplay={togglePlay}
								onsound={toggleSound}
								onfullscreen={toggleFullscreen}
							/>
						</div>
					</div>
				</div>

				{#if !fullscreen}
					<aside
						class={[
							'hidden shrink-0 flex-col gap-6 md:flex',
							shape === 'landscape'
								? 'w-full max-w-5xl justify-between md:flex-row md:items-end'
								: 'w-80'
						]}
					>
						<VideoDetails {video} {position} />
						<PlayerControls
							{paused}
							{muted}
							{fullscreen}
							onplay={togglePlay}
							onsound={toggleSound}
							onfullscreen={toggleFullscreen}
						/>
					</aside>
				{/if}
			</div>
		</div>

		{#if !fullscreen}
			<aside class="hidden w-46 shrink-0 overflow-hidden border-l border-line bg-bg p-3 xl:block">
				<Filmstrip items={stream.items} position={stream.position} onpick={(i) => stream.go(i)} />
			</aside>
		{/if}

		{#if stream.next?.playback_url}
			<!-- Warm the next video so the step forward starts at once. -->
			<video
				src={stream.next.playback_url}
				preload="auto"
				muted
				aria-hidden="true"
				tabindex="-1"
				class="pointer-events-none absolute h-px w-px opacity-0"
			></video>
		{/if}
	</div>
{/if}
