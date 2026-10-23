<script lang="ts">
	import type { VideoSort } from '#lib/api/client.ts';

	type Props = { value: VideoSort; onchange: (sort: VideoSort) => void };

	let { value, onchange }: Props = $props();

	const ORDERS: Array<{ value: VideoSort; label: string }> = [
		{ value: 'newest', label: 'newest' },
		{ value: 'oldest', label: 'oldest' }
	];
</script>

<div role="group" aria-label="Order" class="flex gap-1">
	{#each ORDERS as order (order.value)}
		{@const active = order.value === value}
		<button
			type="button"
			aria-pressed={active}
			onclick={() => {
				if (!active) onchange(order.value);
			}}
			class={[
				'px-2 py-1',
				active ? 'text-accent underline underline-offset-4' : 'text-faint hover:text-fg'
			]}
		>
			{order.label}
		</button>
	{/each}
</div>
