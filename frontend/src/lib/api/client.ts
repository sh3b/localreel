import createClient from 'openapi-fetch';
import type { components, paths } from './schema';

// nginx serves the API under /api (and the Vite dev server proxies it the same
// way), so the client always talks to its own origin.
export const api = createClient<paths>({ baseUrl: '/api' });

export type VideoCard = components['schemas']['VideoCard'];
export type VideoPage = components['schemas']['VideoPage'];
export type VideoSort = components['schemas']['VideoSort'];
export type VideoStatus = components['schemas']['VideoStatus'];
export type QueueItem = components['schemas']['QueueItem'];
export type SubmitResult = components['schemas']['SubmitResult'];

// The API asks who submitted a link. Until there are accounts, everything is
// submitted by this one guest user and shared.
export const GUEST_USER_ID = '00000000-0000-0000-0000-000000000000';
