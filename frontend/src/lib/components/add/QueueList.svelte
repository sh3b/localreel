<script lang="ts">
	import { STATUS_LABEL } from '#lib/add/status.ts';
	import type { QueueItem } from '#lib/api/client.ts';
	import { secondaryButton } from '#lib/components/buttons.ts';

	type Props = { items: QueueItem[]; retrying: Set<string>; onretry: (id: string) => void };

	let { items, retrying, onretry }: Props = $props();
</script>

{#if items.length === 0}
	<p class="p-4 leading-relaxed text-faint">
		Nothing in progress. New links show up here while they download and get ready.
	</p>
{:else}
	<ul aria-label="In progress and failed">
		{#each items as item (item.id)}
			{@const info = item.status === 'READY' ? null : STATUS_LABEL[item.status]}
			{@const failed = item.status === 'FAILED'}
			<li
				class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 border-b border-line px-4 py-3"
			>
				<p class="truncate text-fg-strong">{item.title ?? item.source_url ?? 'Untitled video'}</p>
				<p class={failed ? 'text-danger' : 'text-accent'}>{info?.label}</p>
				<p class={['col-start-1 leading-relaxed', failed ? 'text-danger' : 'text-faint']}>
					{failed ? (item.error_message ?? 'The download failed.') : info?.note}
				</p>
				{#if failed}
					<button
						type="button"
						class={[secondaryButton, 'row-span-1 justify-self-end']}
						disabled={retrying.has(item.id)}
						onclick={() => onretry(item.id)}
					>
						{retrying.has(item.id) ? 'retrying…' : 'retry'}
					</button>
				{/if}
			</li>
		{/each}
	</ul>
{/if}
