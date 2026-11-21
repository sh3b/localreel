<script lang="ts">
	import type { VideoCard } from '#lib/api/client.ts';
	import ExternalLink from '#lib/components/ExternalLink.svelte';
	import VideoTitle from '#lib/components/VideoTitle.svelte';
	import { formatDate, formatDuration, webPageUrl } from '#lib/videos/format.ts';

	type Props = { video: VideoCard };

	let { video }: Props = $props();
</script>

<div class="flex flex-col gap-3.5">
	<VideoTitle
		title={video.title}
		lines={3}
		as="h1"
		hover
		class="font-title text-xl leading-snug font-medium text-fg-strong"
	/>
	<dl class="grid grid-cols-[4.5rem_1fr] gap-x-3 gap-y-1.5 leading-relaxed text-muted">
		{#if video.uploader}
			<dt>by</dt>
			<dd class="text-fg">
				<ExternalLink href={video.uploader_url}>{video.uploader}</ExternalLink>
			</dd>
		{/if}
		{#if video.duration_sec !== null}
			<dt>length</dt>
			<dd class="text-fg">{formatDuration(video.duration_sec)}</dd>
		{/if}
		<dt>saved</dt>
		<dd class="text-fg">{formatDate(video.saved_at)}</dd>
		<!-- No source row without a link: "open original" as plain text means nothing. -->
		{#if webPageUrl(video.source_url)}
			<dt>source</dt>
			<dd class="text-fg">
				<ExternalLink href={video.source_url}>open original</ExternalLink>
			</dd>
		{/if}
	</dl>
</div>
