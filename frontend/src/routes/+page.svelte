<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '#lib/api/client.ts';
	import { shell } from '#lib/shell/shell.svelte.ts';

	let ready = $state<number | null>(null);
	let failed = $state(false);

	onMount(async () => {
		shell.hints = [];
		const { data, error } = await api.GET('/videos', { params: { query: { limit: 100 } } });
		if (error || !data) {
			failed = true;
			return;
		}
		ready = data.items.length;
		shell.status = `${ready}${data.next_cursor ? '+' : ''} ready`;
	});
</script>

<section class="flex h-full items-center justify-center p-6">
	{#if failed}
		<p class="text-danger">The server did not answer. Check that the api container is running.</p>
	{:else if ready === null}
		<p class="text-faint">Loading…</p>
	{:else}
		<p class="text-muted">{ready} videos are ready. The feed player is not built yet.</p>
	{/if}
</section>
