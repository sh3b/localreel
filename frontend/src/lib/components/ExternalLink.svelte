<script lang="ts">
	import type { Snippet } from 'svelte';
	import { webPageUrl } from '#lib/videos/format.ts';

	// A link out of localreel: a new tab, no referrer, and only to a web page
	// (webPageUrl). Without one, the text shows as plain text.
	type Props = { href: string | null; children: Snippet };

	let { href, children }: Props = $props();

	const link = $derived(webPageUrl(href));
</script>

{#if link}
	<!-- An external page, so SvelteKit's resolve() does not apply. -->
	<!-- eslint-disable svelte/no-navigation-without-resolve -->
	<a
		href={link}
		target="_blank"
		rel="noreferrer"
		class="underline decoration-line-strong underline-offset-4 hover:decoration-accent"
		>{@render children()}</a
	>
	<!-- eslint-enable svelte/no-navigation-without-resolve -->
{:else}
	{@render children()}
{/if}
