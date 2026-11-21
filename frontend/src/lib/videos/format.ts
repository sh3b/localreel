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
	if (hours === 0) return `${minutes}:${secs}`;
	return `${hours}:${String(minutes).padStart(2, '0')}:${secs}`;
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

// Only ever link to a web page: a javascript: or data: URL in an href would run
// in this site. Links come from users (the source) and from the video's site
// through yt-dlp (the uploader).
export function webPageUrl(url: string | null): string | null {
	return url && /^https?:\/\//i.test(url) ? url : null;
}
