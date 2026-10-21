<script lang="ts">
	import type { VideoCard } from '#lib/api/client.ts';
	import { formatDate, formatDuration } from '#lib/videos/format.ts';

	type Props = { video: VideoCard; position: string };

	let { video, position }: Props = $props();
</script>

<div class="flex flex-col gap-3.5">
	<p class="text-accent">{position}</p>
	<h1 class="font-title text-xl leading-snug font-medium text-fg-strong">
		{video.title ?? 'Untitled video'}
	</h1>
	<dl class="grid grid-cols-[4.5rem_1fr] gap-x-3 gap-y-1.5 leading-relaxed text-muted">
		{#if video.uploader}
			<dt>by</dt>
			<dd class="text-fg">{video.uploader}</dd>
		{/if}
		{#if video.duration_sec !== null}
			<dt>length</dt>
			<dd class="text-fg">{formatDuration(video.duration_sec)}</dd>
		{/if}
		<dt>saved</dt>
		<dd class="text-fg">{formatDate(video.saved_at)}</dd>
		{#if video.tags.length > 0}
			<dt>tags</dt>
			<dd class="text-accent">{video.tags.map((tag) => `#${tag}`).join(' ')}</dd>
		{/if}
		{#if video.source_url}
			<dt>source</dt>
			<dd>
				<!-- An external page, so SvelteKit's resolve() does not apply. -->
				<!-- eslint-disable svelte/no-navigation-without-resolve -->
				<a
					href={video.source_url}
					target="_blank"
					rel="noreferrer"
					class="text-fg underline decoration-line-strong underline-offset-4 hover:decoration-accent"
					>open original</a
				>
				<!-- eslint-enable svelte/no-navigation-without-resolve -->
			</dd>
		{/if}
	</dl>
</div>
