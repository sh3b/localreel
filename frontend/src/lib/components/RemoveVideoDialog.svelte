<script lang="ts">
	import type { VideoCard } from '#lib/api/client.ts';
	import ConfirmDialog from '#lib/components/ConfirmDialog.svelte';
	import VideoTitle from '#lib/components/VideoTitle.svelte';

	// Asks before removing a video, from the Feed and from the Library.
	type Props = { video: VideoCard; onconfirm: () => void; oncancel: () => void };

	let { video, onconfirm, oncancel }: Props = $props();
</script>

<ConfirmDialog
	title="Remove this video?"
	message="Its file is deleted from this server. This can't be undone."
	confirmLabel="remove"
	{onconfirm}
	{oncancel}
>
	<VideoTitle title={video.title} lines={2} class="mt-2 text-fg" />
</ConfirmDialog>
