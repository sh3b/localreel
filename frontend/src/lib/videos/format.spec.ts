import { describe, expect, it } from 'vitest';
import { formatDate, formatDuration, shapeOf, webPageUrl } from './format.ts';

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

describe('webPageUrl', () => {
	it('keeps http and https links', () => {
		expect(webPageUrl('https://www.youtube.com/@jawed')).toBe('https://www.youtube.com/@jawed');
		expect(webPageUrl('HTTP://example.com')).toBe('HTTP://example.com');
	});

	it('drops anything that is not a web page', () => {
		expect(webPageUrl('javascript:alert(1)')).toBeNull();
		expect(webPageUrl('data:text/html,<script>alert(1)</script>')).toBeNull();
		expect(webPageUrl(' https://example.com')).toBeNull();
		expect(webPageUrl('')).toBeNull();
		expect(webPageUrl(null)).toBeNull();
	});
});
