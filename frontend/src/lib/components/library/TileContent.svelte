<script lang="ts">
	import type { VideoCard } from '#lib/api/client.ts';
	import { formatDuration, shapeOf } from '#lib/videos/format.ts';

	// The inside of a Library tile. Tall for every video: wide ones are cropped
	// to fill it and marked "wide" so the crop is no surprise.
	type Props = { video: VideoCard };

	let { video }: Props = $props();
	const wide = $derived(shapeOf(video.width, video.height) === 'landscape');
</script>

<span class="relative block aspect-[3/4] w-full overflow-hidden bg-surface">
	{#if video.thumbnail_url}
		<img
			src={video.thumbnail_url}
			alt=""
			loading="lazy"
			decoding="async"
			class="h-full w-full object-cover"
		/>
	{/if}
	{#if wide}
		<span class="absolute top-1.5 left-1.5 border border-white/80 px-1 text-[10px] text-white">
			wide
		</span>
	{/if}
	{#if video.duration_sec !== null}
		<span class="absolute top-1.5 right-1.5 bg-black/70 px-1.5 text-[10px] text-white">
			{formatDuration(video.duration_sec)}
		</span>
	{/if}
	<span
		class="absolute inset-x-0 bottom-0 flex flex-col gap-0.5 bg-gradient-to-t from-black/90 to-transparent px-2 pt-7 pb-1.5 text-left"
	>
		<span class="line-clamp-2 text-[11px] leading-tight text-white">
			{video.title ?? 'Untitled video'}
		</span>
		{#if video.tags.length > 0}
			<span class="truncate text-[10px] text-accent">
				{video.tags.map((tag) => `#${tag}`).join(' ')}
			</span>
		{/if}
	</span>
</span>
