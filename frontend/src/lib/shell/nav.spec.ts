import { describe, expect, it } from 'vitest';
import { isActive } from './nav';

describe('isActive', () => {
	it('marks the feed active only on the root path', () => {
		expect(isActive('/', '/')).toBe(true);
		expect(isActive('/', '/library')).toBe(false);
	});

	it('marks a section active on its own path and below it', () => {
		expect(isActive('/library', '/library')).toBe(true);
		expect(isActive('/library', '/library/anything')).toBe(true);
		expect(isActive('/add', '/library')).toBe(false);
	});
});
