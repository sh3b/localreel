import type { QueueItem } from '#lib/api/client.ts';

// Plain words for where a video is on its way to the library.
export const STATUS_LABEL: Record<QueueItem['status'], { label: string; note: string | null }> = {
	PENDING: { label: 'waiting', note: null },
	DOWNLOADING: { label: 'downloading', note: 'Fetching the best quality available.' },
	FAILED: { label: 'failed', note: null }
};
