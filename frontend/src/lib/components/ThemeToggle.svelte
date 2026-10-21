<script lang="ts">
	import { onMount } from 'svelte';
	import {
		THEMES,
		applyTheme,
		nextTheme,
		readSavedTheme,
		type ThemeId
	} from '#lib/theme/themes.ts';

	let theme = $state<ThemeId>(THEMES[0].id);
	const label = $derived(THEMES.find((t) => t.id === theme)?.label ?? theme);

	onMount(() => {
		theme = readSavedTheme();
	});

	function toggle() {
		theme = nextTheme(theme);
		applyTheme(theme);
	}
</script>

<button
	type="button"
	onclick={toggle}
	class="shrink-0 border border-line px-2 py-1 text-faint hover:border-line-strong hover:text-fg"
	aria-label="Switch theme, now {label}"
>
	theme: {label}
</button>
