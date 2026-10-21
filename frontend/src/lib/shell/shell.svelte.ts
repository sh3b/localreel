export type KeyHint = { keys: string; action: string };

// What the current page shows in the shared chrome: a short status at the right
// of the top bar and the keyboard hints in the footer. Pages set it in an effect.
class Shell {
	status = $state('');
	hints = $state<KeyHint[]>([]);
}

export const shell = new Shell();

// Shortcuts must not fire while someone is typing in a field.
export function isTyping(event: KeyboardEvent): boolean {
	const target = event.target;
	if (!(target instanceof HTMLElement)) return false;
	return (
		target.isContentEditable ||
		target instanceof HTMLInputElement ||
		target instanceof HTMLTextAreaElement ||
		target instanceof HTMLSelectElement
	);
}
