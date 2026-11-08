import createClient from 'openapi-fetch';
import type { components, paths } from './schema';

// The UI calls the API under /api on its own origin; the Vite dev server
// proxies it to uvicorn.
export const api = createClient<paths>({ baseUrl: '/api' });

export type QueueItem = components['schemas']['QueueItem'];
export type QueuePage = components['schemas']['QueuePage'];
export type SubmitResult = components['schemas']['SubmitResult'];
export type VideoCard = components['schemas']['VideoCard'];
export type VideoPage = components['schemas']['VideoPage'];
export type VideoSort = components['schemas']['VideoSort'];
