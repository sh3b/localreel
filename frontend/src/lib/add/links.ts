// Must match MAX_LINKS_PER_BATCH in the API (entrypoints/api/schemas/videos.py).
export const MAX_LINKS = 100;

export type LineCheck = 'ok' | 'repeat' | 'not-a-link' | 'over-limit';

export type PastedLine = {
	number: number;
	text: string;
	check: LineCheck;
	repeatOf?: number;
};

// What the paste box shows next to each non-empty line before anything is sent.
export function checkLines(pasted: string): PastedLine[] {
	const seen = new Map<string, number>();
	let accepted = 0;
	const lines: PastedLine[] = [];

	pasted.split('\n').forEach((raw, index) => {
		const text = raw.trim();
		if (!text) return;
		const number = index + 1;
		if (!/^https?:\/\/\S+$/i.test(text)) {
			lines.push({ number, text, check: 'not-a-link' });
		} else if (seen.has(text)) {
			lines.push({ number, text, check: 'repeat', repeatOf: seen.get(text) });
		} else if (accepted >= MAX_LINKS) {
			lines.push({ number, text, check: 'over-limit' });
		} else {
			seen.set(text, number);
			accepted += 1;
			lines.push({ number, text, check: 'ok' });
		}
	});
	return lines;
}

export function linksToSend(lines: PastedLine[]): string[] {
	return lines.filter((line) => line.check === 'ok').map((line) => line.text);
}
