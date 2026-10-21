// Arrow-key movement through a grid of `length` tiles laid out in `columns`.
// Returns the index to focus, or null when the key is not a grid move.
export function gridMove(
	index: number,
	key: string,
	columns: number,
	length: number
): number | null {
	if (length === 0) return null;
	const steps: Record<string, number> = {
		ArrowRight: 1,
		ArrowLeft: -1,
		ArrowDown: columns,
		ArrowUp: -columns,
		Home: -index,
		End: length - 1 - index
	};
	const step = steps[key];
	if (step === undefined) return null;
	const target = index + step;
	// Up from the first row and down from the last row stay where they are.
	if (target < 0 || target > length - 1) return index;
	return target;
}
