import { act, render, screen, waitFor } from "@testing-library/react";
import { ImportLive, POLL_MS, SOCKET_ATTEMPTS, resetLiveTransport } from "../src/components/research/ImportLive";
import * as api from "../src/lib/workspace";

jest.mock("../src/lib/workspace", () => ({ workspaceBase: "", getAccess: () => "memory-token", refreshAccount: jest.fn().mockResolvedValue({ id: "researcher" }), workspaceRequest: jest.fn() }));
class FakeSocket {
  static instances: FakeSocket[] = [];
  onopen?: () => void; onmessage?: (event: { data: string }) => void; onclose?: (event: { code: number }) => void; onerror?: () => void;
  send = jest.fn(); close = jest.fn();
  constructor(public url: string) { FakeSocket.instances.push(this); }
}
const request = api.workspaceRequest as jest.Mock;
const flush = () => act(async () => { for (let i = 0; i < 5; i++) await Promise.resolve(); });

beforeEach(() => {
  FakeSocket.instances = [];
  Object.defineProperty(global, "WebSocket", { configurable: true, value: FakeSocket });
  resetLiveTransport();
  request.mockReset();
});
afterEach(() => { jest.useRealTimers(); });

test("socket authenticates in a message and accepts only valid batch status", async () => {
  const onState = jest.fn();
  const { unmount } = render(<ImportLive batch={{ id: "batch", status: "ready", row_count: 0 }} onState={onState} />);
  await waitFor(() => expect(FakeSocket.instances).toHaveLength(1));
  const socket = FakeSocket.instances[0];
  expect(String(socket.url)).not.toContain("memory-token");
  act(() => socket.onopen?.());
  expect(socket.send).toHaveBeenCalledWith(JSON.stringify({ token: "memory-token" }));
  act(() => socket.onmessage?.({ data: JSON.stringify({ type: "status", id: "other", status: "completed", row_count: 99 }) }));
  expect(onState).not.toHaveBeenCalled();
  act(() => socket.onmessage?.({ data: JSON.stringify({ type: "status", id: "batch", status: "importing", row_count: 0 }) }));
  expect(onState).toHaveBeenCalledWith(expect.objectContaining({ status: "importing" }));
  unmount(); expect(socket.close).toHaveBeenCalled();
});

test("a server refusal switches to authenticated status polling and keeps manual refresh", async () => {
  request.mockResolvedValue({ id: "batch", status: "importing", row_count: 0 });
  const onState = jest.fn();
  render(<ImportLive batch={{ id: "batch", status: "ready", row_count: 0 }} onState={onState} />);
  await waitFor(() => expect(FakeSocket.instances).toHaveLength(1));
  act(() => FakeSocket.instances[0].onclose?.({ code: 1008 }));
  expect(screen.getByText(/Live status is unavailable/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Refresh status" })).toBeInTheDocument();
  await waitFor(() => expect(request).toHaveBeenCalledWith("/research/imports/batch"));
  await waitFor(() => expect(onState).toHaveBeenCalledWith(expect.objectContaining({ status: "importing" })));
  expect(FakeSocket.instances).toHaveLength(1); // no further socket attempts
});

test(`after ${SOCKET_ATTEMPTS} failed connections it polls until the import finishes`, async () => {
  jest.useFakeTimers();
  request
    .mockResolvedValueOnce({ id: "batch", status: "importing", row_count: 0 })
    .mockResolvedValueOnce({ id: "batch", status: "completed", row_count: 12 });
  const onState = jest.fn();
  render(<ImportLive batch={{ id: "batch", status: "ready", row_count: 0 }} onState={onState} />);
  // e.g. a host without WebSocket support: every connection closes abnormally (1006) before opening.
  for (let attempt = 1; attempt <= SOCKET_ATTEMPTS; attempt++) {
    await flush();
    expect(FakeSocket.instances).toHaveLength(attempt);
    act(() => FakeSocket.instances[attempt - 1].onclose?.({ code: 1006 }));
    await act(async () => { jest.advanceTimersByTime(30000); });
  }
  await flush();
  expect(FakeSocket.instances).toHaveLength(SOCKET_ATTEMPTS);
  expect(screen.getByText(/Checking status every few seconds/)).toBeInTheDocument();
  expect(onState).toHaveBeenLastCalledWith(expect.objectContaining({ status: "importing" }));
  await act(async () => { jest.advanceTimersByTime(POLL_MS); });
  await flush();
  expect(onState).toHaveBeenLastCalledWith({ id: "batch", status: "completed", row_count: 12 });
  const calls = request.mock.calls.length;
  await act(async () => { jest.advanceTimersByTime(POLL_MS * 5); });
  expect(request.mock.calls.length).toBe(calls); // terminal state: polling stopped
});

test("once sockets are known to fail, the next import polls immediately and ignores malformed status", async () => {
  request.mockResolvedValue({ id: "other-batch", status: "completed", row_count: 1 });
  const first = render(<ImportLive batch={{ id: "batch", status: "ready", row_count: 0 }} onState={jest.fn()} />);
  await waitFor(() => expect(FakeSocket.instances).toHaveLength(1));
  act(() => FakeSocket.instances[0].onclose?.({ code: 1008 }));
  first.unmount();
  const onState = jest.fn();
  render(<ImportLive batch={{ id: "next", status: "ready", row_count: 0 }} onState={onState} />);
  await waitFor(() => expect(request).toHaveBeenCalledWith("/research/imports/next"));
  expect(FakeSocket.instances).toHaveLength(1); // no new socket for the second import
  expect(onState).not.toHaveBeenCalled(); // a response for a different batch is never reported
});

test("polling errors back off and unmount stops all timers", async () => {
  jest.useFakeTimers();
  request.mockRejectedValue(new Error("offline"));
  const { unmount } = render(<ImportLive batch={{ id: "batch", status: "ready", row_count: 0 }} onState={jest.fn()} />);
  await flush();
  act(() => FakeSocket.instances[0].onclose?.({ code: 1008 }));
  await act(async () => { jest.advanceTimersByTime(0); });
  await flush();
  expect(screen.getByText(/Status check failed/)).toBeInTheDocument();
  expect(request).toHaveBeenCalledTimes(1);
  await act(async () => { jest.advanceTimersByTime(POLL_MS); });
  expect(request).toHaveBeenCalledTimes(1); // backed off beyond the normal interval
  await act(async () => { jest.advanceTimersByTime(POLL_MS * 2); });
  await flush();
  expect(request).toHaveBeenCalledTimes(2);
  unmount();
  await act(async () => { jest.advanceTimersByTime(60000); });
  expect(request).toHaveBeenCalledTimes(2);
});
