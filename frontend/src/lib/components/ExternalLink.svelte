<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { webPageUrl } from '#lib/videos/format.ts';

	// A link out of localreel: a new tab, no referrer, and only to a web page
	// (webPageUrl). Without one, the text shows as plain text. `on` is what it
	// sits on: the page, or the picture (the overlay's colours).
	type Props = {
		href: string | null;
		on?: 'page' | 'media';
		class?: ClassValue;
		children: Snippet;
	};

	let { href, on = 'page', class: extra, children }: Props = $props();

	const UNDERLINE = {
		page: 'decoration-line-strong hover:decoration-accent',
		media: 'decoration-on-media-muted hover:decoration-media-accent'
	} as const;

	const link = $derived(webPageUrl(href));
</script>

{#if link}
	<!-- An external page, so SvelteKit's resolve() does not apply. -->
	<!-- eslint-disable svelte/no-navigation-without-resolve -->
	<a
		href={link}
		target="_blank"
		rel="noreferrer"
		class={['underline underline-offset-4', UNDERLINE[on], extra]}>{@render children()}</a
	>
	<!-- eslint-enable svelte/no-navigation-without-resolve -->
{:else}
	{@render children()}
{/if}
