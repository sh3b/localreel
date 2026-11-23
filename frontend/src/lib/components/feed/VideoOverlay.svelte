<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import type { VideoCard } from '#lib/api/client.ts';
	import ExternalLink from '#lib/components/ExternalLink.svelte';
	import VideoTitle from '#lib/components/VideoTitle.svelte';
	import { formatDuration, webPageUrl } from '#lib/videos/format.ts';

	// The details drawn over the picture: on phones, and in fullscreen. On a
	// wider page they sit beside the video instead (VideoDetails).
	type Props = { video: VideoCard; class?: ClassValue; children: Snippet };

	let { video, class: extra, children }: Props = $props();
</script>

<div
	class={[
		'pointer-events-none absolute inset-x-0 bottom-0 flex flex-col gap-2.5 bg-gradient-to-t from-scrim/90 to-transparent p-4 pt-24 text-on-media transition-opacity',
		extra
	]}
>
	<VideoTitle title={video.title} lines={3} class="font-title text-lg leading-snug font-medium" />
	<!-- The links take taps; the rest of the overlay lets them through to the video. -->
	<p class="flex flex-wrap gap-x-4 gap-y-1 wrap-anywhere text-on-media-muted">
		{#if video.uploader}
			<ExternalLink href={video.uploader_url} on="media" class="pointer-events-auto">
				{video.uploader}
			</ExternalLink>
		{/if}
		{#if video.duration_sec !== null}<span>{formatDuration(video.duration_sec)}</span>{/if}
		{#if webPageUrl(video.source_url)}
			<ExternalLink href={video.source_url} on="media" class="pointer-events-auto">
				open original
			</ExternalLink>
		{/if}
	</p>
	<div class="pointer-events-auto">{@render children()}</div>
</div>
