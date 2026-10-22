<script lang="ts">
	import type { VideoCard } from '#lib/api/client.ts';

	type Props = {
		video: VideoCard;
		muted: boolean;
		onpausedchange: (paused: boolean) => void;
		onended?: () => void;
	};

	// The Feed recreates this component for every video (keyed on its id), so
	// the position, length and play state start fresh. Shared across videos,
	// a replaced video would leak into the next one: bind:currentTime started it
	// where the last one ended, and a replaced video's cancelled play() set
	// bind:paused to true and paused the new one.
	let { video, muted = $bindable(), onpausedchange, onended }: Props = $props();

	let element = $state<HTMLVideoElement>();
	let elementPaused = $state(true);
	let currentTime = $state(0);
	let duration = $state(0);
	const progress = $derived(duration > 0 ? (currentTime / duration) * 100 : 0);

	// The page shows the play state; only this instance, while it lives, reports it.
	$effect(() => {
		onpausedchange(elementPaused);
	});

	export function togglePlay() {
		elementPaused = !elementPaused;
	}

	// Start each new video. If the browser refuses autoplay with sound
	// (NotAllowedError), fall back to muted rather than a frozen frame. Other
	// failures, like the AbortError from skipping on quickly, leave sound alone.
	$effect(() => {
		const el = element;
		if (!el || !video.playback_url) return;
		el.play().catch((error: DOMException) => {
			if (error.name !== 'NotAllowedError') return;
			muted = true;
			el.muted = true;
			el.play().catch(() => {});
		});
	});

	function seek(event: Event) {
		if (element) element.currentTime = Number((event.currentTarget as HTMLInputElement).value);
	}
</script>

<div class="relative h-full w-full bg-media">
	<video
		bind:this={element}
		bind:paused={elementPaused}
		bind:currentTime
		bind:duration
		{muted}
		src={video.playback_url}
		poster={video.thumbnail_url ?? undefined}
		playsinline
		preload="auto"
		{onended}
		onclick={togglePlay}
		class="h-full w-full cursor-pointer object-contain"
	></video>

	<div class="absolute inset-x-0 bottom-0 h-[3px] bg-white/20">
		<div class="h-full bg-accent" style:width="{progress}%"></div>
	</div>
	<input
		type="range"
		min="0"
		max={duration || 0}
		step="0.1"
		value={currentTime}
		oninput={seek}
		aria-label="Position in video"
		class="absolute inset-x-0 -bottom-1.5 h-4 w-full cursor-pointer opacity-0"
	/>
</div>
