export type Shape = 'portrait' | 'landscape' | 'square';

// Most saved videos are vertical, so a missing size is treated as portrait.
export function shapeOf(width: number | null, height: number | null): Shape {
	if (!width || !height) return 'portrait';
	const ratio = width / height;
	if (ratio > 1.1) return 'landscape';
	if (ratio < 0.9) return 'portrait';
	return 'square';
}

export function formatDuration(seconds: number | null): string {
	if (seconds === null || seconds < 0) return '';
	const whole = Math.round(seconds);
	const hours = Math.floor(whole / 3600);
	const minutes = Math.floor((whole % 3600) / 60);
	const secs = String(whole % 60).padStart(2, '0');
	return hours > 0 ? `${hours}:${String(minutes).padStart(2, '0')}:${secs}` : `${minutes}:${secs}`;
}

const dateFormat = new Intl.DateTimeFormat('en-GB', {
	day: 'numeric',
	month: 'short',
	year: 'numeric',
	timeZone: 'UTC'
});

export function formatDate(iso: string): string {
	return dateFormat.format(new Date(iso));
}

// "3/27" while more can still load becomes "3/27+".
export function formatPosition(index: number, loaded: number, complete: boolean): string {
	if (loaded === 0) return '0/0';
	return `${index + 1}/${loaded}${complete ? '' : '+'}`;
}
