// Inputs that take no typed text. They keep focus after a click (a range, a
// checkbox) and must not swallow the shortcuts until a click elsewhere.
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
