"use client";
import { useEffect, useState } from "react";
import { workspaceRequest } from "../../lib/workspace";
import { useQueryParam } from "../../lib/useQueryParam";

const RETURN_NOTICES: Record<string, string> = {
  returned: "You have returned from Stripe. A redirect does not confirm payment; completion is recorded only after Stripe sends a verified event.",
  cancelled: "Checkout was cancelled. You can start again when you are ready.",
};

export function Support() {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [amount, setAmount] = useState(500);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [requestKey, setRequestKey] = useState("");
  useEffect(() => {
    let active = true;
    workspaceRequest<{ enabled: boolean }>("/support/status").then(value => { if (active) setEnabled(value.enabled); })
      .catch(() => { if (active) { setEnabled(false); setError("Support checkout is unavailable. Please try again later."); } });
    return () => { active = false; };
  }, []);
  // Derived from the URL Stripe returned to, not copied into state by an effect.
  const notice = RETURN_NOTICES[useQueryParam("checkout") ?? ""] ?? "";
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
