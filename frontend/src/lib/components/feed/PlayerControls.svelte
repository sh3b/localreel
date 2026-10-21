<script lang="ts">
	// Every keyboard shortcut also has a visible control, for mouse and touch.
	type Props = {
		paused: boolean;
		muted: boolean;
		fullscreen: boolean;
		onplay: () => void;
		onsound: () => void;
		onfullscreen: () => void;
	};

	let { paused, muted, fullscreen, onplay, onsound, onfullscreen }: Props = $props();

	const button =
		'min-h-11 border border-line-strong bg-bg/60 px-3 text-fg hover:border-accent hover:text-fg-strong';
</script>

<div class="flex flex-wrap gap-2">
	<button type="button" class={button} onclick={onplay}>
		<kbd class="text-faint">space</kbd>
		{paused ? 'play' : 'pause'}
	</button>
	<button type="button" class={button} onclick={onsound} aria-pressed={!muted}>
		<kbd class="text-faint">m</kbd>
		{muted ? 'sound on' : 'mute'}
	</button>
	<button type="button" class={button} onclick={onfullscreen}>
		<kbd class="text-faint">f</kbd>
		{fullscreen ? 'exit fullscreen' : 'fullscreen'}
	</button>
</div>
