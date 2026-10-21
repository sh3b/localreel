import { describe, expect, it } from 'vitest';
import { formatDate, formatDuration, formatPosition, shapeOf } from './format';

describe('shapeOf', () => {
	it('tells portrait, landscape and square apart', () => {
		expect(shapeOf(1080, 1920)).toBe('portrait');
		expect(shapeOf(3840, 2160)).toBe('landscape');
		expect(shapeOf(1080, 1080)).toBe('square');
		expect(shapeOf(320, 240)).toBe('landscape');
	});

	it('treats an unknown size as portrait', () => {
		expect(shapeOf(null, null)).toBe('portrait');
		expect(shapeOf(0, 1920)).toBe('portrait');
	});
});

describe('formatDuration', () => {
	it('shows minutes and seconds, and hours only when needed', () => {
		expect(formatDuration(213)).toBe('3:33');
		expect(formatDuration(19)).toBe('0:19');
		expect(formatDuration(3725)).toBe('1:02:05');
	});

	it('shows nothing for an unknown length', () => {
		expect(formatDuration(null)).toBe('');
	});
});

describe('formatDate', () => {
	it('shows day, short month and year', () => {
		expect(formatDate('2026-10-21T00:08:55.567Z')).toBe('21 Oct 2026');
	});
});

describe('formatPosition', () => {
	it('marks that more videos can still load', () => {
		expect(formatPosition(2, 27, false)).toBe('3/27+');
		expect(formatPosition(26, 27, true)).toBe('27/27');
		expect(formatPosition(0, 0, true)).toBe('0/0');
	});
});
