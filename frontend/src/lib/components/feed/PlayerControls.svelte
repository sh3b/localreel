<script lang="ts">
	import { controlButton } from '#lib/components/buttons.ts';

	// Every keyboard shortcut also has a visible control, for mouse and touch.
	type Props = {
		paused: boolean;
		muted: boolean;
		fullscreen: boolean;
		canFullscreen: boolean;
		onplay: () => void;
		onsound: () => void;
		onfullscreen: () => void;
	};

	let { paused, muted, fullscreen, canFullscreen, onplay, onsound, onfullscreen }: Props = $props();
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
</div>
