import type { VideoStatus } from '#lib/api/client.ts';

// Plain words for where a video is in the pipeline.
export const STATUS_LABEL: Record<
	Exclude<VideoStatus, 'READY'>,
	{ label: string; note: string }
> = {
	PENDING: { label: 'waiting', note: 'In line. Starts when a worker is free.' },
	DOWNLOADING: { label: 'downloading', note: 'Fetching the best quality available.' },
	DOWNLOADED: { label: 'downloaded', note: 'Waiting to be made playable.' },
	TRANSCODING: {
		label: 'preparing',
		note: 'Making a copy every browser can play. Longer videos take a few minutes.'
	},
	FAILED: { label: 'failed', note: '' }
};

export function isWorking(status: VideoStatus): boolean {
	return status !== 'FAILED' && status !== 'READY';
}
