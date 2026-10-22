<script lang="ts">
	import type { VideoCard } from '#lib/api/client.ts';

	type Props = { items: VideoCard[]; position: number; onpick: (index: number) => void };

	let { items, position, onpick }: Props = $props();

	// The current video and the next two.
	const visible = $derived(
		items
			.slice(position, position + 3)
			.map((video, offset) => ({ video, index: position + offset }))
	);
</script>

<nav aria-label="Now playing and up next" class="flex flex-col gap-3">
	{#each visible as { video, index } (video.id)}
		{@const current = index === position}
		<button
			type="button"
			onclick={() => onpick(index)}
			aria-current={current ? 'true' : undefined}
			aria-label="Play {video.title ?? 'video'}"
			class={[
				'relative aspect-[3/4] w-full shrink-0 overflow-hidden bg-surface',
				current ? 'outline-2 -outline-offset-2 outline-accent' : 'opacity-55 hover:opacity-90'
			]}
		>
			{#if video.thumbnail_url}
				<img src={video.thumbnail_url} alt="" loading="lazy" class="h-full w-full object-cover" />
			{/if}
			<span class="absolute bottom-1.5 left-1.5 bg-bg/75 px-1 text-[10px] text-fg">
				{String(index + 1).padStart(2, '0')}
			</span>
		</button>
	{/each}
</nav>
