<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import type { VideoCard } from '#lib/api/client.ts';
	import { formatDuration } from '#lib/videos/format.ts';

	// The details drawn over the picture: on phones, and in fullscreen. On a
	// desktop page they sit beside the video instead (VideoDetails).
	type Props = { video: VideoCard; position: string; class?: ClassValue; children: Snippet };

	let { video, position, class: extra, children }: Props = $props();
</script>

<div
	class={[
		'pointer-events-none absolute inset-x-0 bottom-0 flex flex-col gap-2.5 bg-gradient-to-t from-black/90 to-transparent p-4 pt-24 text-white transition-opacity',
		extra
	]}
>
	<p class="text-accent">{position}</p>
	<p class="font-title text-lg leading-snug font-medium">{video.title ?? 'Untitled video'}</p>
	<p class="text-white/75">
		{[video.uploader, formatDuration(video.duration_sec)].filter(Boolean).join(', ')}
	</p>
	{#if video.tags.length > 0}
		<p class="text-accent">{video.tags.map((tag) => `#${tag}`).join(' ')}</p>
	{/if}
	<div class="pointer-events-auto">{@render children()}</div>
</div>
