<script lang="ts">
	import type { Snippet } from 'svelte';

	// The centred message for empty, error and end-of-list screens.
	type Props = { marker?: string; title: string; children?: Snippet; actions?: Snippet };

	let { marker, title, children, actions }: Props = $props();
</script>

<section class="flex h-full items-center justify-center p-6">
	<div class="flex w-full max-w-md flex-col gap-4">
		{#if marker}<p class="text-accent">{marker}</p>{/if}
		<h1 class="font-title text-2xl leading-tight font-medium text-fg-strong">{title}</h1>
		{#if children}<div class="leading-relaxed text-muted">{@render children()}</div>{/if}
		{#if actions}<div class="mt-2 flex flex-wrap gap-3">{@render actions()}</div>{/if}
	</div>
</section>
