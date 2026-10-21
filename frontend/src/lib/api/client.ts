import createClient from 'openapi-fetch';
import type { components, paths } from './schema';

// nginx serves the API under /api (and the Vite dev server proxies it the same
// way), so the client always talks to its own origin.
export const api = createClient<paths>({ baseUrl: '/api' });

export type VideoCard = components['schemas']['VideoCard'];
export type VideoPage = components['schemas']['VideoPage'];
export type VideoSort = components['schemas']['VideoSort'];
