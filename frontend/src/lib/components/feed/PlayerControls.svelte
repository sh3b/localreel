<script lang="ts">
	import { controlButton } from '#lib/components/buttons.ts';

	// Every keyboard shortcut also has a visible control, for mouse and touch.
	type Props = {
		paused: boolean;
		muted: boolean;
		fullscreen: boolean;
		canFullscreen: boolean;
		removing: boolean;
		onplay: () => void;
		onsound: () => void;
		onfullscreen: () => void;
		onremove: () => void;
	};

	let {
		paused,
		muted,
		fullscreen,
		canFullscreen,
		removing,
		onplay,
		onsound,
		onfullscreen,
		onremove
	}: Props = $props();
</script>

<div class="flex flex-wrap gap-2">
	<button type="button" class={controlButton} onclick={onplay}>
		<kbd class="text-faint">space</kbd>
		{paused ? 'play' : 'pause'}
	</button>
	<button type="button" class={controlButton} onclick={onsound} aria-pressed={!muted}>
		<kbd class="text-faint">m</kbd>
		{muted ? 'sound on' : 'mute'}
	</button>
	{#if canFullscreen}
		<button type="button" class={controlButton} onclick={onfullscreen}>
			<kbd class="text-faint">f</kbd>
			{fullscreen ? 'exit fullscreen' : 'fullscreen'}
		</button>
	{/if}
	<button type="button" class={controlButton} onclick={onremove} disabled={removing}>
		<kbd class="text-faint">x</kbd>
		{removing ? 'removing…' : 'remove'}
	</button>
</div>
