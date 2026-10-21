<script lang="ts">
	import { shell } from '#lib/shell/shell.svelte.ts';

	$effect(() => {
		shell.status = '';
		shell.hints = [];
	});
</script>

<section class="flex h-full items-center justify-center p-6">
	<p class="text-muted">The library is not built yet.</p>
</section>
