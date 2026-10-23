<script lang="ts">
	import { onMount } from 'svelte';
	import type { SubmitResult } from '#lib/api/client.ts';
	import { checkLines, linksToSend, MAX_LINKS, type PastedLine } from '#lib/add/links.ts';
	import { AddQueue } from '#lib/add/queue.svelte.ts';
	import QueueList from '#lib/components/add/QueueList.svelte';
	import { primaryButton } from '#lib/components/buttons.ts';
	import { isTyping, shell } from '#lib/shell/shell.svelte.ts';
	import { stream } from '#lib/videos/stream.svelte.ts';

	// When a video becomes ready, the Feed and the Library load afresh next time.
	const queue = new AddQueue(() => stream.invalidate());

	let pasted = $state('');
	let results = $state<SubmitResult[] | null>(null);
	let skipped = $state(0);
	let textarea = $state<HTMLTextAreaElement>();

	const lines = $derived(checkLines(pasted));
	const toSend = $derived(linksToSend(lines));

	const NOTE: Record<PastedLine['check'], { text: (line: PastedLine) => string; tone: string }> = {
		ok: { text: () => 'ok', tone: 'text-faint' },
		repeat: { text: (line) => `same as line ${line.repeatOf}`, tone: 'text-warn' },
		'not-a-link': { text: () => 'not a link', tone: 'text-danger' },
		'over-limit': { text: () => `over ${MAX_LINKS}, send it next time`, tone: 'text-danger' }
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
		return queue.watch();
	});

	$effect(() => {
		const parts = [];
		if (queue.workingCount > 0) parts.push(`${queue.workingCount} in progress`);
		if (queue.failedCount > 0) parts.push(`${queue.failedCount} failed`);
		shell.status = parts.join(', ');
	});

	async function send() {
		if (toSend.length === 0 || queue.sending) return;
		// The box stays editable while sending, so count from what was sent.
		const links = toSend;
		const notSent = lines.length - links.length;
		const sent = await queue.send(links);
		if (!sent) return;
		skipped = notSent;
		results = sent;
		pasted = '';
	}

	function addMore() {
		results = null;
		queueMicrotask(() => textarea?.focus());
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
					{#each results as result (result.url)}
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
								<span class={NOTE[line.check].tone}>{NOTE[line.check].text(line)}</span>
							</li>
						{/each}
					</ol>
				{/if}

				{#if queue.sendFailed}
					<p class="text-danger">
						The links could not be sent. Check that the localreel containers are running.
					</p>
				{/if}

				<div class="flex flex-wrap items-center gap-4">
					<button
						type="submit"
						class={primaryButton}
						disabled={toSend.length === 0 || queue.sending}
					>
						{#if queue.sending}
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
		{#if queue.loadFailed}
			<p class="p-4 text-danger">The queue could not be loaded. Retrying every few seconds.</p>
		{/if}
		<QueueList items={queue.items} retrying={queue.retrying} onretry={(id) => queue.retry(id)} />
	</section>
</div>
