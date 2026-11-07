// A request the server never answers would leave its button busy, or stop
// the polling, for good. Every request is given up after this long instead,
// and fails like any other.
const REQUEST_TIMEOUT_MS = 10_000;

export async function withTimeout<T>(request: (signal: AbortSignal) => Promise<T>): Promise<T> {
	const giveUp = new AbortController();
	const timer = setTimeout(() => giveUp.abort(), REQUEST_TIMEOUT_MS);
	try {
		return await request(giveUp.signal);
	} finally {
		clearTimeout(timer);
	}
}
