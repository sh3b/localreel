<script lang="ts">
	import type { Snippet } from 'svelte';
	import { primaryButton, secondaryButton } from '#lib/components/buttons.ts';

	// Asks before something that can't be undone. Shown while it is rendered;
	// Escape cancels. Cancel comes first, so it is the button that has focus.
	// children: what it is about (a video's title), shown above the message.
	type Props = {
		title: string;
		message: string;
		confirmLabel: string;
		onconfirm: () => void;
		oncancel: () => void;
		children?: Snippet;
	};

	let { title, message, confirmLabel, onconfirm, oncancel, children }: Props = $props();

	let dialog = $state<HTMLDialogElement>();

	// Focus goes back where it was when the dialog opened, so a keyboard user
	// keeps their place; the browser does not do this for a removed dialog.
	$effect(() => {
		const element = dialog;
		if (!element) return;
		const opener = document.activeElement;
		element.showModal();
		return () => {
			element.close();
			if (opener instanceof HTMLElement) opener.focus();
		};
	});
</script>

<dialog
	bind:this={dialog}
	oncancel={(event) => {
		event.preventDefault();
		oncancel();
	}}
	aria-labelledby="confirm-title"
	class="m-auto max-w-sm border border-line-strong bg-surface p-5 text-fg backdrop:bg-scrim/70"
>
	<h2 id="confirm-title" class="font-title text-lg font-medium text-fg-strong">{title}</h2>
	{@render children?.()}
	<p class="mt-2 leading-relaxed text-muted">{message}</p>
	<div class="mt-5 flex flex-wrap justify-end gap-3">
		<button type="button" class={secondaryButton} onclick={oncancel}>cancel</button>
		<button type="button" class={primaryButton} onclick={onconfirm}>{confirmLabel}</button>
	</div>
</dialog>
