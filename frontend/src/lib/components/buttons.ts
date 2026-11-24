// Shared button looks, so every page's actions match.
export const primaryButton =
	'inline-flex min-h-11 items-center gap-2 border border-accent bg-accent px-4 font-bold text-on-accent hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50';

export const secondaryButton =
	'inline-flex min-h-11 items-center gap-2 border border-line-strong px-4 text-fg hover:border-accent hover:text-fg-strong disabled:cursor-not-allowed disabled:opacity-50';

// Player controls, half see-through so they also sit over the video. Less
// padding on phones, so the Feed's four fit on one row at 360 px with their
// usual labels ("exit fullscreen" and "removing…" may wrap).
export const controlButton =
	'min-h-11 border border-line-strong bg-bg/60 px-2 text-fg md:px-3 hover:border-accent hover:text-fg-strong disabled:cursor-not-allowed disabled:opacity-50';
