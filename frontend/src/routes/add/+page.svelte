<script lang="ts">
	import { onMount } from 'svelte';
	import { SvelteSet } from 'svelte/reactivity';
	import { GUEST_USER_ID, api, type QueueItem, type SubmitResult } from '#lib/api/client.ts';
	import { checkLines, linksToSend, MAX_LINKS, type PastedLine } from '#lib/add/links.ts';
	import { isWorking } from '#lib/add/status.ts';
	import QueueList from '#lib/components/add/QueueList.svelte';
	import { primaryButton } from '#lib/components/buttons.ts';
	import { isTyping, shell } from '#lib/shell/shell.svelte.ts';
	import { stream } from '#lib/videos/stream.svelte.ts';

	const POLL_MS = 3000;

	let pasted = $state('');
	let sending = $state(false);
	let sendError = $state<string | null>(null);
	let results = $state<SubmitResult[] | null>(null);
	let skipped = $state(0);
	let queue = $state<QueueItem[]>([]);
	let queueError = $state(false);
	const retrying = new SvelteSet<string>();
	let textarea = $state<HTMLTextAreaElement>();

	const lines = $derived(checkLines(pasted));
	const toSend = $derived(linksToSend(lines));
	const failedCount = $derived(queue.filter((item) => item.status === 'FAILED').length);
	const workingCount = $derived(queue.filter((item) => isWorking(item.status)).length);

	const NOTE: Record<PastedLine['check'], (line: PastedLine) => string> = {
		ok: () => 'ok',
		repeat: (line) => `same as line ${line.repeatOf}`,
		'not-a-link': () => 'not a link',
		'over-limit': () => `over ${MAX_LINKS}, send it next time`
	};

	const RESULT: Record<SubmitResult['result'], { label: string; tone: string }> = {
		queued: { label: 'queued', tone: 'text-ok' },
		ready: { label: 'already in your library', tone: 'text-warn' },
		failed: { label: 'failed earlier, retry it in the queue', tone: 'text-danger' },
		unsupported: { label: 'not supported', tone: 'text-danger' }
	};

	onMount(() => {
		shell.hints = [
			{ keys: 'ctrl+enter', action: 'add' },
			{ keys: 'n', action: 'add more after sending' }
		];
		textarea?.focus();
		void refreshQueue();
		const timer = setInterval(refreshQueue, POLL_MS);
		return () => clearInterval(timer);
	});

	$effect(() => {
		const parts = [];
		if (workingCount > 0) parts.push(`${workingCount} in progress`);
		if (failedCount > 0) parts.push(`${failedCount} failed`);
		shell.status = parts.join(', ');
	});

	async function refreshQueue() {
		const { data, error } = await api.GET('/videos/queue');
		if (error || !data) {
			queueError = true;
			return;
		}
		queueError = false;
		// A video that was in progress and has left the queue is ready to watch.
		const stillQueued = new Set(data.map((item) => item.id));
		if (queue.some((item) => isWorking(item.status) && !stillQueued.has(item.id))) {
			stream.invalidate();
		}
		queue = data;
	}

	async function send() {
		if (toSend.length === 0 || sending) return;
		sending = true;
		sendError = null;
		const { data, error } = await api.POST('/videos/batch', {
			body: { urls: toSend, user_id: GUEST_USER_ID, visibility: 'SHARED' }
		});
		sending = false;
		if (error || !data) {
			sendError = 'The links could not be sent. Check that the localreel containers are running.';
			return;
		}
		skipped = lines.length - toSend.length;
		results = data;
		pasted = '';
		void refreshQueue();
	}

	function addMore() {
		results = null;
		queueMicrotask(() => textarea?.focus());
	}

	async function retry(id: string) {
		retrying.add(id);
		await api.POST('/videos/{video_id}/retry', { params: { path: { video_id: id } } });
		await refreshQueue();
		retrying.delete(id);
	}

	function onkeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
			event.preventDefault();
			void send();
		} else if (event.key === 'n' && results && !isTyping(event)) {
			event.preventDefault();
			addMore();
		}
	}
</script>

<svelte:window {onkeydown} />

<div
	class="h-full overflow-y-auto md:grid md:grid-cols-[minmax(0,34rem)_minmax(0,1fr)] md:overflow-hidden"
>
	<section class="flex flex-col border-line md:min-h-0 md:overflow-y-auto md:border-r">
		{#if results}
			<div class="flex flex-col gap-4 p-4">
				<h1 class="font-title text-xl font-medium text-fg-strong">
					{results.length}
					{results.length === 1 ? 'link' : 'links'} sent
				</h1>
				<ul class="border-t border-line">
					{#each results as result, index (index)}
						<li class="flex flex-col gap-0.5 border-b border-line py-2.5">
							<span class="flex justify-between gap-4">
								<span class="truncate text-fg">{result.url}</span>
								<span class={['shrink-0', RESULT[result.result].tone]}>
									{RESULT[result.result].label}
								</span>
							</span>
							{#if result.reason}<span class="text-faint">{result.reason}</span>{/if}
						</li>
					{/each}
				</ul>
				{#if skipped > 0}
					<p class="text-faint">
						{skipped}
						{skipped === 1 ? 'line was' : 'lines were'} not sent: not a link, a repeat, or over the limit.
					</p>
				{/if}
				<div>
					<button type="button" class={primaryButton} onclick={addMore}>
						<kbd>n</kbd> add more
					</button>
				</div>
			</div>
		{:else}
			<form
				class="flex flex-col gap-3 p-4"
				onsubmit={(event) => {
					event.preventDefault();
					void send();
				}}
			>
				<label for="links" class="text-faint">Paste links, one per line</label>
				<textarea
					id="links"
					bind:this={textarea}
					bind:value={pasted}
					rows="8"
					spellcheck="false"
					autocomplete="off"
					placeholder="https://www.youtube.com/watch?v=…"
					class="min-h-40 resize-y border border-line-strong bg-surface p-3 leading-relaxed text-fg placeholder:text-faint focus:border-accent focus:outline-none"
				></textarea>

				{#if lines.length > 0}
					<ol aria-label="What will be sent" class="flex flex-col gap-0.5">
						{#each lines as line (line.number)}
							<li class="grid grid-cols-[2rem_minmax(0,1fr)_auto] gap-3">
								<span class="text-right text-faint">{line.number}</span>
								<span class={['truncate', line.check === 'ok' ? 'text-fg' : 'text-muted']}>
									{line.text}
								</span>
								<span
									class={line.check === 'ok'
										? 'text-faint'
										: line.check === 'repeat'
											? 'text-warn'
											: 'text-danger'}
								>
									{NOTE[line.check](line)}
								</span>
							</li>
						{/each}
					</ol>
				{/if}

				{#if sendError}<p class="text-danger">{sendError}</p>{/if}

				<div class="flex flex-wrap items-center gap-4">
					<button type="submit" class={primaryButton} disabled={toSend.length === 0 || sending}>
						{#if sending}
							sending…
						{:else if toSend.length === 0}
							add links
						{:else}
							add {toSend.length}
							{toSend.length === 1 ? 'link' : 'links'}
						{/if}
					</button>
					<span class="hidden text-faint md:inline">ctrl+enter from the box</span>
				</div>
				<p class="leading-relaxed text-faint">
					Links download in the background and appear in the feed once they are ready to play.
					YouTube, TikTok and Facebook links are supported.
				</p>
			</form>
		{/if}
	</section>

	<section
		aria-label="Queue"
		class="border-t border-line md:min-h-0 md:overflow-y-auto md:border-t-0"
	>
		<h2 class="flex h-bar items-center border-b border-line px-4 text-faint">queue</h2>
		{#if queueError}
			<p class="p-4 text-danger">The queue could not be loaded. Retrying every few seconds.</p>
		{/if}
		<QueueList items={queue} {retrying} onretry={retry} />
	</section>
</div>

<style>
	button:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
