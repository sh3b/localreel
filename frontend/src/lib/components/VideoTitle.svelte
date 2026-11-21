<script lang="ts">
	import type { ClassValue } from 'svelte/elements';
	import { titleOf } from '#lib/videos/format.ts';

	// A video's title, wherever it shows. Clamped to a few lines with "…": a
	// Facebook title is its whole caption, often paragraphs. A word longer than
	// the line (a link as a title) wraps instead of running out.
	// hover: with a mouse, hovering shows all of it. Only where the title is
	// the thing to read (the Feed details): over a grid of tiles it would pop
	// up on every move, and over the video the mouse goes to the video.
	type Props = {
		title: string | null;
		lines: 2 | 3;
		as?: 'h1' | 'p' | 'span';
		hover?: boolean;
		class?: ClassValue;
	};

	let { title, lines, as = 'p', hover = false, class: extra }: Props = $props();

	// Whole class names, so Tailwind finds them.
	const CLAMP = { 2: 'line-clamp-2', 3: 'line-clamp-3' } as const;
</script>

<svelte:element
	this={as}
	title={hover ? (title ?? undefined) : undefined}
	class={[CLAMP[lines], 'wrap-anywhere', extra]}
>
	{titleOf(title)}
</svelte:element>
