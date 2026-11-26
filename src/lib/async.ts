/**
 * Promise helpers for the prediction request.
 *
 * Callbacks vs promises: `setTimeout` is a callback API. You hand it a function and it calls that function
 * later; it returns nothing you can wait on, chain, or combine, and errors cannot flow back to the caller.
 * `delay` wraps it in a Promise, so the same timer can be awaited, raced, cancelled through an AbortSignal and
 * handled with try/catch. `withTimeout` then uses `Promise.race` to give any request a deadline.
 *
 * The assessment page uses both styles on purpose: a plain callback for the "starting the model" notice (fire
 * and forget, nothing waits on it) and `withTimeout` for the request itself (the code must wait for, and
 * branch on, whichever finishes first).
 */

/** Thrown by `withTimeout` when the deadline passes before the task settles. */
export class TimeoutError extends Error {
  constructor(public readonly ms: number) {
    super(`Timed out after ${ms} ms`);
    this.name = "TimeoutError";
  }
}

function abortError(signal: AbortSignal): unknown {
  return signal.reason ?? new DOMException("The operation was aborted.", "AbortError");
}

/**
 * A promise that resolves after `ms` milliseconds: `setTimeout`'s callback turned into a promise.
 * If `signal` aborts first, the timer is cleared and the promise rejects with the abort reason.
 */
export function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(abortError(signal));
      return;
    }
    const onAbort = () => {
      clearTimeout(id);
      reject(abortError(signal as AbortSignal));
    };
    const id = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

/**
 * Settles like `task`, unless `ms` passes first: then it rejects with a `TimeoutError` and aborts
 * `controller` (if given) so the underlying request stops too. The timer is always cleared, so nothing
 * keeps running after the task has finished.
 */
export async function withTimeout<T>(task: Promise<T>, ms: number, controller?: AbortController): Promise<T> {
  const timer = new AbortController();
  const deadline = delay(ms, timer.signal).then(() => {
    const error = new TimeoutError(ms);
    controller?.abort(error);
    throw error;
  });
  try {
    return await Promise.race([task, deadline]);
  } finally {
    timer.abort(); // clears the pending setTimeout when the task won the race
    deadline.catch(() => undefined); // the losing deadline's abort rejection is expected; never report it
  }
}
