import { describe, expect, it } from 'vitest';
import { gridMove } from './grid';

describe('gridMove', () => {
	// 10 tiles in rows of 4:  0 1 2 3 / 4 5 6 7 / 8 9
	it('moves one tile left and right, and one row up and down', () => {
		expect(gridMove(5, 'ArrowRight', 4, 10)).toBe(6);
		expect(gridMove(5, 'ArrowLeft', 4, 10)).toBe(4);
		expect(gridMove(5, 'ArrowDown', 4, 10)).toBe(9);
		expect(gridMove(5, 'ArrowUp', 4, 10)).toBe(1);
	});

	it('stays put at the edges instead of jumping out of the grid', () => {
		expect(gridMove(1, 'ArrowUp', 4, 10)).toBe(1);
		expect(gridMove(7, 'ArrowDown', 4, 10)).toBe(7);
		expect(gridMove(9, 'ArrowRight', 4, 10)).toBe(9);
	});

	it('stays put moving down onto the gap of a short last row', () => {
		expect(gridMove(6, 'ArrowDown', 4, 10)).toBe(6);
	});

	it('jumps to the first and last tile', () => {
		expect(gridMove(5, 'Home', 4, 10)).toBe(0);
		expect(gridMove(5, 'End', 4, 10)).toBe(9);
	});

	it('ignores other keys and empty grids', () => {
		expect(gridMove(5, 'Enter', 4, 10)).toBeNull();
		expect(gridMove(0, 'ArrowRight', 4, 0)).toBeNull();
	});
});
