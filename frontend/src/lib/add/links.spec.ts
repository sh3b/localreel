import { describe, expect, it } from 'vitest';
import { checkLines, linksToSend, MAX_LINKS } from './links';

describe('checkLines', () => {
	it('numbers lines as typed and skips blank ones', () => {
		const lines = checkLines('https://youtu.be/a\n\n  https://youtu.be/b  \n');

		expect(lines.map((l) => [l.number, l.text, l.check])).toEqual([
			[1, 'https://youtu.be/a', 'ok'],
			[3, 'https://youtu.be/b', 'ok']
		]);
	});

	it('flags text that is not a link', () => {
		expect(checkLines('pasta recipe')[0].check).toBe('not-a-link');
		expect(checkLines('youtu.be/a')[0].check).toBe('not-a-link');
	});

	it('flags a link repeated in the same paste and points at the first one', () => {
		const lines = checkLines('https://youtu.be/a\nhttps://youtu.be/a');

		expect(lines[1]).toMatchObject({ check: 'repeat', repeatOf: 1 });
	});

	it('flags links past the limit of one request', () => {
		const pasted = Array.from({ length: MAX_LINKS + 2 }, (_, i) => `https://youtu.be/${i}`);
		const lines = checkLines(pasted.join('\n'));

		expect(lines.filter((l) => l.check === 'ok')).toHaveLength(MAX_LINKS);
		expect(lines.at(-1)?.check).toBe('over-limit');
	});
});

describe('linksToSend', () => {
	it('sends only the accepted links', () => {
		const lines = checkLines('https://youtu.be/a\nnope\nhttps://youtu.be/a\nhttps://youtu.be/b');

		expect(linksToSend(lines)).toEqual(['https://youtu.be/a', 'https://youtu.be/b']);
	});
});
