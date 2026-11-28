import { act, render, screen, waitFor } from "@testing-library/react";
import { ImportLive } from "../src/components/research/ImportLive";
import * as api from "../src/lib/workspace";

jest.mock("../src/lib/workspace", () => ({ workspaceBase: "", getAccess: () => "memory-token", refreshAccount: jest.fn().mockResolvedValue({ id: "researcher" }), workspaceRequest: jest.fn() }));
class FakeSocket {
  static instances: FakeSocket[] = [];
  onopen?: () => void; onmessage?: (event: { data: string }) => void; onclose?: (event: { code: number }) => void; onerror?: () => void;
  send = jest.fn(); close = jest.fn();
  constructor(public url: string) { FakeSocket.instances.push(this); }
}
beforeEach(() => { FakeSocket.instances = []; Object.defineProperty(global, "WebSocket", { configurable: true, value: FakeSocket }); });

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

test("authorization refusal stops reconnecting and offers refresh", async () => {
  render(<ImportLive batch={{ id: "batch", status: "ready", row_count: 0 }} onState={jest.fn()} />);
  await waitFor(() => expect(FakeSocket.instances).toHaveLength(1));
  act(() => FakeSocket.instances[0].onclose?.({ code: 1008 }));
  expect(screen.getByText(/Live status is unavailable/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Refresh status" })).toBeInTheDocument();
});
