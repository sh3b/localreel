<script lang="ts">
	import '../app.css';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import ThemeToggle from '#lib/components/ThemeToggle.svelte';
	import { NAV, isActive } from '#lib/shell/nav.ts';
	import { isTyping, shell } from '#lib/shell/shell.svelte.ts';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	function onkeydown(event: KeyboardEvent) {
		if (isTyping(event) || event.metaKey || event.ctrlKey || event.altKey) return;
		const item = NAV.find((n) => n.key === event.key);
		if (item) {
			event.preventDefault();
			goto(resolve(item.href));
		}
	}
</script>

<svelte:window {onkeydown} />

<div class="flex h-dvh flex-col bg-bg text-fg">
	<header class="flex h-bar shrink-0 items-center gap-6 border-b border-line px-4">
		<a href={resolve('/')} class="text-[13px] font-bold text-accent">localreel</a>
		<nav aria-label="Main" class="hidden h-full items-stretch gap-6 md:flex">
			{#each NAV as item (item.href)}
				{@const active = isActive(item.href, page.url.pathname)}
				<a
					href={resolve(item.href)}
					aria-current={active ? 'page' : undefined}
					class={[
						'flex items-center border-b-2',
						active ? 'border-accent text-fg-strong' : 'border-transparent text-faint hover:text-fg'
					]}
				>
					<span class="mr-1.5 text-faint">{item.key}</span>{item.label}
				</a>
			{/each}
		</nav>
		<p class="ml-auto truncate text-faint">{shell.status}</p>
		<ThemeToggle />
	</header>

	<main class="min-h-0 flex-1">
		{@render children()}
	</main>

	{#if shell.hints.length > 0}
		<footer
			class="hidden h-9 shrink-0 items-center gap-6 border-t border-line px-4 text-faint md:flex"
			aria-label="Keyboard shortcuts"
		>
			{#each shell.hints as hint (hint.keys)}
				<span><kbd class="font-ui font-bold text-fg">{hint.keys}</kbd> {hint.action}</span>
			{/each}
		</footer>
	{/if}

	<nav aria-label="Main" class="grid h-14 shrink-0 grid-cols-3 border-t border-line md:hidden">
		{#each NAV as item (item.href)}
			{@const active = isActive(item.href, page.url.pathname)}
			<a
				href={resolve(item.href)}
				aria-current={active ? 'page' : undefined}
				class={[
					'flex items-center justify-center border-t-2 text-[13px]',
					active ? 'border-accent text-accent' : 'border-transparent text-faint'
				]}
			>
				{item.label}
			</a>
		{/each}
	</nav>
</div>
