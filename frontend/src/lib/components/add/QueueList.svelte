<script lang="ts">
	import { STATUS_LABEL } from '#lib/add/status.ts';
	import type { QueueItem } from '#lib/api/client.ts';
	import { secondaryButton } from '#lib/components/buttons.ts';

	type Props = {
		items: QueueItem[];
		waitingNotShown: number;
		retrying: Set<string>;
		onretry: (id: string) => void;
	};

	let { items, waitingNotShown, retrying, onretry }: Props = $props();
</script>

{#if items.length === 0}
	<p class="p-4 leading-relaxed text-faint">
		Nothing in progress. New links show up here while they download.
	</p>
{:else}
	<p class="border-b border-line px-4 py-3 text-faint">
		One video downloads at a time, oldest first.
	</p>
	<ul aria-label="In progress and failed">
		{#each items as item (item.id)}
			{@const info = item.status === 'READY' ? null : STATUS_LABEL[item.status]}
			{@const failed = item.status === 'FAILED'}
			<li
				class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 border-b border-line px-4 py-3"
			>
				<p class="truncate text-fg-strong">{item.source_url}</p>
				<p class={['justify-self-end', failed ? 'text-danger' : 'text-accent']}>{info?.label}</p>
				{#if failed}
					<p class="col-start-1 leading-relaxed text-danger">
						{item.error ?? 'The download failed.'}
					</p>
					<button
						type="button"
						class={[secondaryButton, 'justify-self-end']}
						disabled={retrying.has(item.id)}
						onclick={() => onretry(item.id)}
					>
						{retrying.has(item.id) ? 'retrying…' : 'retry'}
					</button>
				{:else if info?.note}
					<p class="col-start-1 leading-relaxed text-faint">{info.note}</p>
				{/if}
			</li>
		{/each}
	</ul>
	{#if waitingNotShown > 0}
		<p class="p-4 text-faint">{waitingNotShown} more waiting</p>
	{/if}
{/if}
