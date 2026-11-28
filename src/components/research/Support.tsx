"use client";
import { useEffect, useState } from "react";
import { workspaceRequest } from "../../lib/workspace";

export function Support() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [amount, setAmount] = useState(500);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [requestKey, setRequestKey] = useState("");
  useEffect(() => {
    let active = true;
    workspaceRequest<{ enabled: boolean }>("/support/status").then(value => { if (active) setEnabled(value.enabled); })
      .catch(() => { if (active) { setEnabled(false); setError("Support checkout is unavailable. Please try again later."); } });
    const returned = new URLSearchParams(window.location.search).get("checkout");
    if (returned === "returned") setNotice("You have returned from Stripe. A redirect does not confirm payment; completion is recorded only after Stripe sends a verified event.");
    if (returned === "cancelled") setNotice("Checkout was cancelled. You can start again when you are ready.");
    return () => { active = false; };
  }, []);
  return <div className="workspace-content">
    {enabled === null && <p role="status">Checking test checkout availability…</p>}
    {enabled === false && <p className="workspace-status">Test checkout has not been enabled on this deployment.</p>}
    {notice && <p className="workspace-status" role="status">{notice}</p>}
    {error && <p className="workspace-error" role="alert">{error}</p>}
    {enabled && <form onSubmit={async event => {
      event.preventDefault(); setBusy(true); setError("");
      const key = requestKey || crypto.randomUUID(); setRequestKey(key);
      try {
        const result = await workspaceRequest<{ url: string }>("/support/checkout", { method: "POST", body: JSON.stringify({ amount, request_key: key }) });
        const url = new URL(result.url);
        if (url.protocol !== "https:" || url.hostname !== "checkout.stripe.com") throw new Error("Checkout returned an invalid destination.");
        window.location.assign(url.href);
      } catch (error) { setError((error as Error).message); setBusy(false); }
    }}>
      <fieldset className="workspace-amounts" disabled={busy}><legend>Choose a test amount (USD)</legend>{[500, 1000, 2500].map(value => <label key={value}><input type="radio" name="amount" checked={amount === value} value={value} onChange={() => { setAmount(value); setRequestKey(""); }} />${value / 100}</label>)}</fieldset>
      <p>Stripe test mode only. No real money is collected. Use Stripe&apos;s test payment details, never a real card.</p>
      <button className="btn-primary" disabled={busy}>{busy ? "Opening Stripe…" : "Open test checkout"}</button>
    </form>}
  </div>;
}
