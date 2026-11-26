/**
 * Promises vs callbacks (src/lib/async.ts): `delay` turns setTimeout's callback into a promise, and
 * `withTimeout` races a task against that promise. Fake timers make the timing exact.
 */
import { TimeoutError, delay, withTimeout } from '../src/lib/async';

beforeEach(() => jest.useFakeTimers());
afterEach(() => jest.useRealTimers());

describe('callback vs promise', () => {
  it('a callback runs later but gives the caller nothing to wait on', () => {
    const order: string[] = [];
    const returned = setTimeout(() => order.push('callback ran'), 100);
    order.push('caller continues');
    jest.advanceTimersByTime(100);
    expect(order).toEqual(['caller continues', 'callback ran']);
    expect(returned).not.toBeInstanceOf(Promise);
  });

  it('delay wraps the same timer in a promise the caller can await', async () => {
    const order: string[] = [];
    const waiting = delay(100).then(() => order.push('resolved'));
    order.push('caller continues');
    expect(order).toEqual(['caller continues']);
    await jest.advanceTimersByTimeAsync(100);
    await waiting;
    expect(order).toEqual(['caller continues', 'resolved']);
  });
});

describe('delay', () => {
  it('rejects with the abort reason and clears its timer when aborted', async () => {
    const controller = new AbortController();
    const waiting = delay(1_000, controller.signal);
    controller.abort(new Error('reset'));
    await expect(waiting).rejects.toThrow('reset');
    expect(jest.getTimerCount()).toBe(0);
  });

  it('rejects at once when the signal is already aborted', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(delay(10, controller.signal)).rejects.toMatchObject({ name: 'AbortError' });
    expect(jest.getTimerCount()).toBe(0);
  });
});

describe('withTimeout', () => {
  it('returns the task result and leaves no timer running', async () => {
    const task = delay(50).then(() => 'result');
    const result = withTimeout(task, 1_000);
    await jest.advanceTimersByTimeAsync(50);
    await expect(result).resolves.toBe('result');
    expect(jest.getTimerCount()).toBe(0);
  });

  it('passes the task error through unchanged', async () => {
    const failing = Promise.reject(new Error('503 from API'));
    await expect(withTimeout(failing, 1_000)).rejects.toThrow('503 from API');
    expect(jest.getTimerCount()).toBe(0);
  });

  it('rejects with TimeoutError at the deadline and aborts the request', async () => {
    const controller = new AbortController();
    const never = new Promise<string>(() => {});
    const result = withTimeout(never, 75_000, controller);
    const check = expect(result).rejects.toBeInstanceOf(TimeoutError);
    await jest.advanceTimersByTimeAsync(75_000);
    await check;
    expect(controller.signal.aborted).toBe(true);
    expect(controller.signal.reason).toBeInstanceOf(TimeoutError);
  });

  it('does not time out a task that finishes just before the deadline', async () => {
    const result = withTimeout(delay(74_999).then(() => 'in time'), 75_000);
    await jest.advanceTimersByTimeAsync(74_999);
    await expect(result).resolves.toBe('in time');
  });
});
