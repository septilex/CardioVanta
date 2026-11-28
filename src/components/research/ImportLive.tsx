"use client";

import { useEffect, useState } from "react";
import { getAccess, refreshAccount, workspaceBase, workspaceRequest, type ImportState } from "../../lib/workspace";

export function ImportLive({ batch, onState }: { batch: ImportState; onState: (value: ImportState) => void }) {
  const [connection, setConnection] = useState("Connecting to live status…");
  useEffect(() => {
    if (["completed", "failed"].includes(batch.status)) return;
    let stopped = false, socket: WebSocket | undefined, timer: ReturnType<typeof setTimeout> | undefined;
    let heartbeat: ReturnType<typeof setTimeout> | undefined, delay = 1000;
    const reconnect = () => {
      if (stopped) return;
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
          if (value.type === "status" && value.id === batch.id && ["ready", "validating", "importing", "completed", "failed"].includes(value.status) && Number.isInteger(value.row_count) && value.row_count >= 0) {
            alive(); delay = 1000; onState(value);
          }
        } catch { setConnection("Waiting for a valid status update…"); }
      };
      socket.onclose = event => {
        clearTimeout(heartbeat);
        if (event.code === 1000 || event.code === 1008) {
          if (!stopped) setConnection(event.code === 1008 ? "Live status is unavailable. Use Refresh status." : "Import status received.");
          return;
        }
        reconnect();
      };
      socket.onerror = () => { if (!stopped) setConnection("Live connection unavailable. You can refresh status below."); };
    };
    void connect();
    return () => { stopped = true; clearTimeout(timer); clearTimeout(heartbeat); socket?.close(); };
  }, [batch.id, batch.status, onState]);

  return <div className="workspace-status" aria-live="polite">
    <p><strong>Import: {batch.status}</strong>{batch.status === "completed" && ` · ${batch.row_count} metric rows saved`}</p>
    {!["completed", "failed"].includes(batch.status) && <p>{connection}</p>}
    {batch.notice && <p>{batch.notice}</p>}
    <button type="button" className="workspace-link" onClick={async () => {
      try { onState(await workspaceRequest<ImportState>(`/research/imports/${batch.id}`)); }
      catch (error) { setConnection((error as Error).message); }
    }}>Refresh status</button>
  </div>;
}
