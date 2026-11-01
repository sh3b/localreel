export type KeyHint = { keys: string; action: string };

// What the current page shows in the shared chrome: a short status at the right
// of the top bar and the keyboard hints in the footer.
class Shell {
	status = $state('');
	hints = $state<KeyHint[]>([]);
}

export const shell = new Shell();
