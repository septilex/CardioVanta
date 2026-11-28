"use client";

import { useEffect, useState } from "react";
import { getAccess, refreshAccount, workspaceBase, workspaceRequest, type ImportState } from "../../lib/workspace";

const STATUSES = ["ready", "validating", "importing", "completed", "failed"];
const TERMINAL = ["completed", "failed"];
/** Consecutive failed socket connections before switching to HTTP polling. */
export const SOCKET_ATTEMPTS = 3;
export const POLL_MS = 3000;

/** Set once WebSockets are known not to work here (e.g. Vercel serverless functions cannot host a socket server),
 * so later imports on this page start polling immediately instead of repeating the failed attempts. */
let socketsUnavailable = false;
export function resetLiveTransport() { socketsUnavailable = false; }

function validState(value: unknown, id: string): value is ImportState {
  const v = value as ImportState;
  return !!v && v.id === id && STATUSES.includes(v.status) && Number.isInteger(v.row_count) && v.row_count >= 0;
}

export function ImportLive({ batch, onState }: { batch: ImportState; onState: (value: ImportState) => void }) {
  const [connection, setConnection] = useState("Connecting to live status…");
  useEffect(() => {
    if (TERMINAL.includes(batch.status)) return;
    let stopped = false, socket: WebSocket | undefined, timer: ReturnType<typeof setTimeout> | undefined;
    let heartbeat: ReturnType<typeof setTimeout> | undefined, delay = 1000, failures = 0;
    const report = (value: ImportState) => {
      if (value.status !== batch.status || value.row_count !== batch.row_count) onState(value);
    };

    // Fallback transport: the same authenticated, owner-scoped status endpoint, read on an interval.
    const poll = async (wait = POLL_MS) => {
      if (stopped) return;
      try {
        const value = await workspaceRequest<ImportState>(`/research/imports/${batch.id}`);
        if (stopped) return;
        if (validState(value, batch.id)) {
          report(value);
          if (TERMINAL.includes(value.status)) return;
        }
        wait = POLL_MS;
      } catch {
        if (stopped) return;
        setConnection("Status check failed. Retrying…");
        wait = Math.min(wait * 2, 15000);
      }
      timer = setTimeout(() => void poll(wait), wait);
    };
    const startPolling = (message: string) => {
      if (stopped) return;
      socketsUnavailable = true;
      clearTimeout(heartbeat);
      setConnection(message);
      timer = setTimeout(() => void poll(), 0);
    };

    const reconnect = () => {
      if (stopped) return;
      failures += 1;
      if (failures >= SOCKET_ATTEMPTS) {
        startPolling("Live connection unavailable here. Checking status every few seconds.");
        return;
      }
      setConnection("Connection interrupted. Reconnecting…");
      timer = setTimeout(connect, delay);
      delay = Math.min(delay * 2, 30000);
    };
    const alive = () => {
      clearTimeout(heartbeat);
      heartbeat = setTimeout(() => socket?.close(), 25000);
    };
    const connect = async () => {
      await refreshAccount();
      if (stopped) return;
      if (!getAccess()) { setConnection("Sign in again to follow live status."); return; }
      const url = new URL(`${workspaceBase}/api/v1/research/imports/${batch.id}/live`, window.location.origin);
      url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
      socket = new WebSocket(url);
      socket.onopen = () => { socket?.send(JSON.stringify({ token: getAccess() })); setConnection("Live status connected"); alive(); };
      socket.onmessage = event => {
        try {
          const value = JSON.parse(event.data);
          if (value.type === "heartbeat") { alive(); return; }
          if (value.type === "status" && validState(value, batch.id)) {
            alive(); delay = 1000; failures = 0; onState(value);
          }
        } catch { setConnection("Waiting for a valid status update…"); }
      };
      socket.onclose = event => {
        clearTimeout(heartbeat);
        if (stopped) return;
        if (event.code === 1000) { setConnection("Import status received."); return; }
        if (event.code === 1008) {
          // The server refused the socket (live status disabled, wrong origin or not authorised for it).
          startPolling("Live status is unavailable. Checking status every few seconds instead.");
          return;
        }
        reconnect();
      };
      socket.onerror = () => { if (!stopped) setConnection("Live connection unavailable. Retrying…"); };
    };

    if (socketsUnavailable) startPolling("Checking status every few seconds.");
    else void connect();
    return () => { stopped = true; clearTimeout(timer); clearTimeout(heartbeat); socket?.close(); };
  }, [batch.id, batch.status, batch.row_count, onState]);

  return <div className="workspace-status" aria-live="polite">
    <p><strong>Import: {batch.status}</strong>{batch.status === "completed" && ` · ${batch.row_count} metric rows saved`}</p>
    {!TERMINAL.includes(batch.status) && <p>{connection}</p>}
    {batch.notice && <p>{batch.notice}</p>}
    <button type="button" className="workspace-link" onClick={async () => {
      try { onState(await workspaceRequest<ImportState>(`/research/imports/${batch.id}`)); }
      catch (error) { setConnection((error as Error).message); }
    }}>Refresh status</button>
  </div>;
}
