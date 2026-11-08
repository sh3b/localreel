<script lang="ts">
	import { STATUS_LABEL } from '#lib/add/status.ts';
	import type { QueueItem } from '#lib/api/client.ts';
	import { secondaryButton } from '#lib/components/buttons.ts';

	type Props = {
		items: QueueItem[];
		waitingNotShown: number;
		retrying: Set<string>;
		removing: Set<string>;
		onretry: (id: string) => void;
		onremove: (id: string) => void;
	};

	let { items, waitingNotShown, retrying, removing, onretry, onremove }: Props = $props();
</script>

{#if items.length === 0}
	<p class="p-4 leading-relaxed text-faint">
		Nothing in progress. New links show up here while they download.
	</p>
{:else}
	<p class="border-b border-line px-4 py-3 text-faint">
		One video downloads at a time, oldest first.
	</p>
	<!-- Wide: one grid for all rows, so labels and buttons line up down the list.
	     Narrow: the buttons move under the link, so the link stays readable. -->
	<div class="@container">
		<ul
			aria-label="In progress and failed"
			class="@lg:grid @lg:grid-cols-[minmax(0,1fr)_auto_auto]"
		>
			{#each items as item (item.id)}
				{@const info = STATUS_LABEL[item.status]}
				{@const failed = item.status === 'FAILED'}
				{@const busy = retrying.has(item.id) || removing.has(item.id)}
				<li
					class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 border-b border-line px-4 py-2 @lg:col-span-3 @lg:grid-cols-subgrid"
				>
					<p class="truncate text-fg-strong">{item.source_url}</p>
					<p class={['justify-self-end', failed ? 'text-danger' : 'text-accent']}>
						{info.label}
					</p>
					{#if failed}
						<p class="col-span-full leading-relaxed text-danger">
							{item.error ?? 'The download failed.'}
						</p>
					{:else if info.note}
						<p class="col-span-full leading-relaxed text-faint">{info.note}</p>
					{/if}
					{#if item.status !== 'DOWNLOADING'}
						<div
							class="col-span-full flex justify-end gap-2 @lg:col-span-1 @lg:col-start-3 @lg:row-start-1"
						>
							{#if failed}
								<button
									type="button"
									class={secondaryButton}
									disabled={busy}
									onclick={() => onretry(item.id)}
								>
									{retrying.has(item.id) ? 'retrying…' : 'retry'}
								</button>
							{/if}
							<button
								type="button"
								class={secondaryButton}
								disabled={busy}
								onclick={() => onremove(item.id)}
							>
								{removing.has(item.id) ? 'removing…' : 'remove'}
							</button>
						</div>
					{/if}
				</li>
			{/each}
		</ul>
	</div>
	{#if waitingNotShown > 0}
		<p class="p-4 text-faint">{waitingNotShown} more waiting</p>
	{/if}
{/if}
