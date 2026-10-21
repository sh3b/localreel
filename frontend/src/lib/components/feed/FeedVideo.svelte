<script lang="ts">
	import type { VideoCard } from '#lib/api/client.ts';

	type Props = {
		video: VideoCard;
		muted: boolean;
		paused: boolean;
		onended?: () => void;
	};

	// The Feed recreates this component for every video (keyed on its id), so
	// the position and length start fresh; kept across videos, bind:currentTime
	// would start the next one where the last one ended.
	let { video, muted = $bindable(), paused = $bindable(), onended }: Props = $props();

	let element = $state<HTMLVideoElement>();
	let currentTime = $state(0);
	let duration = $state(0);
	const progress = $derived(duration > 0 ? (currentTime / duration) * 100 : 0);

	// Start each new video. If the browser refuses autoplay with sound, fall
	// back to muted rather than showing a frozen frame.
	$effect(() => {
		const el = element;
		if (!el || !video.playback_url) return;
		el.play().catch(() => {
			muted = true;
			el.muted = true;
			el.play().catch(() => (paused = true));
		});
	});

	function seek(event: Event) {
		if (element) element.currentTime = Number((event.currentTarget as HTMLInputElement).value);
	}
</script>

<div class="relative h-full w-full bg-media">
	<video
		bind:this={element}
		bind:paused
		bind:currentTime
		bind:duration
		{muted}
		src={video.playback_url}
		poster={video.thumbnail_url ?? undefined}
		playsinline
		preload="auto"
		{onended}
		onclick={() => (paused = !paused)}
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
