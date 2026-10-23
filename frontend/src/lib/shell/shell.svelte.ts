export type KeyHint = { keys: string; action: string };

// What the current page shows in the shared chrome: a short status at the right
// of the top bar and the keyboard hints in the footer. Pages set it in an effect.
class Shell {
	status = $state('');
	hints = $state<KeyHint[]>([]);
}

export const shell = new Shell();

// Inputs that take no typed text. They keep focus after a click (the Feed's
// seek bar is a range), and must not swallow the shortcuts until a click elsewhere.
const NOT_TEXT = [
	'button',
	'checkbox',
	'color',
	'file',
	'hidden',
	'image',
	'radio',
	'range',
	'reset',
	'submit'
];

// Shortcuts must not fire while someone is typing in a field.
export function isTyping(event: KeyboardEvent): boolean {
	const target = event.target;
	if (!(target instanceof HTMLElement)) return false;
	return (
		target.isContentEditable ||
		(target instanceof HTMLInputElement && !NOT_TEXT.includes(target.type)) ||
		target instanceof HTMLTextAreaElement ||
		target instanceof HTMLSelectElement
	);
}
