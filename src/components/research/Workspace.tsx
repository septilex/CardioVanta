"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { afterStatusUpdate, refreshAccount, setAccess, workspaceBase, workspaceRequest, type Account, type ImportState } from "../../lib/workspace";
import { ImportLive } from "./ImportLive";
import { useQueryParam } from "../../lib/useQueryParam";

const LOGIN_FAILED = "Google sign-in failed or was cancelled. If you already have an account, sign in with your password and link Google.";

export function Workspace() {
  const [account, setAccount] = useState<Account | null>(null);
  const [available, setAvailable] = useState<{ enabled: boolean; google: boolean } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [batch, setBatch] = useState<ImportState | null>(null);
  const [users, setUsers] = useState<Account[]>([]);
  const [feedback, setFeedback] = useState<{ id: string; section: string; helpful: boolean; model_version: string }[]>([]);
  const [section, setSection] = useState("summary");
  const [events, setEvents] = useState<{ action: string; fields: string[]; created_at: string }[] | null>(null);
  const updateBatch = useCallback((value: ImportState) => setBatch(value), []);

  useEffect(() => {
    let active = true;
    workspaceRequest<{ enabled: boolean; google: boolean }>("/auth/status")
      .then(async status => { if (active) setAvailable(status); if (status.enabled) { const user = await refreshAccount(); if (active) setAccount(user); } })
      .catch(() => { if (active) setError("Account service is unavailable. Please reload to try again."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  // The OAuth callback redirects here with ?login=failed. Shown until the reader does something else.
  const loginFailed = useQueryParam("login") === "failed";
  const [loginNoticeDismissed, setLoginNoticeDismissed] = useState(false);
  const shownError = error || (loginFailed && !loginNoticeDismissed ? LOGIN_FAILED : "");

  async function act(task: () => Promise<void>) {
    setBusy(true); setError(""); setNotice(""); setLoginNoticeDismissed(true);
    try { await task(); } catch (error) { setError((error as Error).message); } finally { setBusy(false); }
  }

  async function authenticate(event: FormEvent) {
    event.preventDefault();
    await act(async () => {
      const result = await workspaceRequest<{ access_token: string; user: Account }>(`/auth/${register ? "register" : "login"}`, { method: "POST", body: JSON.stringify({ email, password }) });
      setAccess(result.access_token); setAccount(result.user); setPassword("");
    });
  }

  const researcher = account?.roles.some(role => ["researcher", "admin"].includes(role));
  const admin = account?.roles.includes("admin");
  if (loading) return <p role="status">Checking account access…</p>;

  return <div className="workspace-content">
    {shownError && <p className="workspace-error" role="alert">{shownError}</p>}
    {notice && <p className="workspace-status" role="status">{notice}</p>}
    {available && !available.enabled && <p className="workspace-status">The research workspace has not been enabled on this deployment. <Link href="/research">Public research</Link> and <Link href="/assessment">Heart Analysis</Link> remain available.</p>}
    {!account && available?.enabled && <section aria-labelledby="account-heading">
      <h2 id="account-heading">{register ? "Create a research account" : "Sign in to your workspace"}</h2>
      <p>New accounts have viewer access. An administrator can grant import permissions.</p>
      <form onSubmit={authenticate} className="workspace-form">
        <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required maxLength={254} autoComplete="email" /></label>
        <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={register ? 12 : 1} maxLength={128} autoComplete={register ? "new-password" : "current-password"} aria-describedby={register ? "password-policy" : undefined} /></label>
        {register && <p id="password-policy">Use 12–128 characters, including a letter and a number.</p>}
        <button className="btn-primary" disabled={busy}>{busy ? "Please wait…" : register ? "Create account" : "Sign in"}</button>
        <button type="button" className="workspace-link" disabled={busy} onClick={() => { setRegister(!register); setError(""); setLoginNoticeDismissed(true); }}>{register ? "Already registered? Sign in" : "Create a viewer account"}</button>
      </form>
      {available.google && <a className="workspace-link" href={`${workspaceBase}/api/v1/auth/google`}>Continue with Google</a>}
    </section>}
    {account && <>
      <section className="workspace-account" aria-label="Current account"><p><strong>{account.email}</strong><br />{account.roles.join(", ")}</p>
        <button className="btn-secondary" disabled={busy} onClick={() => act(async () => { await workspaceRequest("/auth/logout", { method: "POST" }); setAccess(""); setAccount(null); setBatch(null); })}>Sign out</button>
      </section>
      <p><Link href="/research">Browse published research and evaluations</Link></p>
      {!researcher && <p className="workspace-status">Your viewer account can browse research. Ask a project administrator for researcher access to import evaluation metrics.</p>}
      {researcher && <section aria-labelledby="import-heading">
        <h2 id="import-heading">Import evaluation metrics</h2>
        <p>Research metadata only. Do not upload patient records, clinical measurements or individual predictions.</p>
        <p>UTF-8 CSV · maximum 256 KiB · 500 rows. <a href="/templates/research-metrics.csv" download>Download the header template</a></p>
        <details><summary>Accepted fields and values</summary><p>Use registered model and cohort codes. Methods: external_validation, nested_cv, holdout. Metrics: roc_auc, accuracy, sensitivity, specificity, brier, ece, log_loss, calibration_slope. Source: a report identifier such as reports/evaluation.md. Existing metrics are never overwritten.</p></details>
        <form className="workspace-form" onSubmit={event => { event.preventDefault(); void act(async () => {
          if (!file || file.size > 262144 || !/^[A-Za-z0-9_-]{1,80}\.csv$/.test(file.name)) throw new Error("Choose a CSV with a simple filename, no larger than 256 KiB.");
          if (!await refreshAccount()) { setAccount(null); throw new Error("Your session expired. Sign in again."); }
          const started = await workspaceRequest<ImportState>("/research/imports", { method: "POST" }); setBatch(started);
          await afterStatusUpdate();
          const body = new FormData(); body.append("file", file);
          try { setBatch(await workspaceRequest<ImportState>(`/research/imports/${started.id}/file`, { method: "POST", body })); }
          catch (error) { try { setBatch(await workspaceRequest<ImportState>(`/research/imports/${started.id}`)); } catch { /* Status can be refreshed after connectivity returns. */ } throw error; }
        }); }}>
          <label>Research CSV<input type="file" accept=".csv,text/csv" required disabled={busy} onChange={event => setFile(event.target.files?.[0] || null)} /></label>
          <button className="btn-primary" disabled={busy || !file}>{busy ? "Importing…" : "Validate and import"}</button>
        </form>
        {batch && <ImportLive batch={batch} onState={updateBatch} />}
      </section>}
      {researcher && <section aria-labelledby="feedback-heading"><h2 id="feedback-heading">Explanation feedback</h2>
        <div className="workspace-actions"><label>Result section<select value={section} onChange={e => setSection(e.target.value)}><option value="summary">Summary</option><option value="why">Why</option><option value="audit">Audit</option></select></label>
          <button className="btn-secondary" disabled={busy} onClick={() => act(async () => { const result = await workspaceRequest<{ feedback: typeof feedback }>(`/research/feedback?section=${section}`); setFeedback(result.feedback); setEvents(null); setNotice(result.feedback.length ? "Latest feedback loaded." : "No feedback for this section yet."); })}>Load latest feedback</button></div>
        <ul>{feedback.map(item => <li key={item.id}>{item.section} · {item.helpful ? "Helpful" : "Not helpful"} · model {item.model_version} <button className="workspace-link" disabled={busy} onClick={() => act(async () => { const result = await workspaceRequest<{ events: NonNullable<typeof events> }>(`/research/feedback/${item.id}/events`); setEvents(result.events); })}>View history</button></li>)}</ul>
        {events && <ol aria-label="Feedback history">{events.map((event, index) => <li key={index}>{event.action} {event.fields.join(", ")} · {new Date(event.created_at).toLocaleString()}</li>)}</ol>}
      </section>}
      {admin && <section aria-labelledby="admin-heading"><h2 id="admin-heading">Account permissions</h2>
        <button className="btn-secondary" disabled={busy} onClick={() => act(async () => setUsers((await workspaceRequest<{ users: Account[] }>("/admin/users")).users))}>Load accounts</button>
        <ul className="workspace-users">{users.map(user => <li key={user.id}><span>{user.email}</span><label>Role for {user.email}<select value={user.roles[0]} disabled={busy || user.id === account.id} onChange={event => { const role = event.target.value; void act(async () => { const changed = await workspaceRequest<Account>(`/admin/users/${user.id}/role`, { method: "PATCH", body: JSON.stringify({ role }) }); setUsers(old => old.map(item => item.id === changed.id ? changed : item)); }); }}><option value="viewer">Viewer</option><option value="researcher">Researcher</option><option value="admin">Admin</option></select></label></li>)}</ul>
      </section>}
      <section aria-labelledby="security-heading"><h2 id="security-heading">Account security</h2>
        {available?.google && <button className="btn-secondary" disabled={busy} onClick={() => act(async () => { const result = await workspaceRequest<{ url: string }>("/auth/google/link", { method: "POST" }); window.location.assign(result.url); })}>Link your Google account</button>}
        <form className="workspace-form" onSubmit={event => { event.preventDefault(); void act(async () => { await workspaceRequest("/auth/password", { method: "POST", body: JSON.stringify({ current_password: password, new_password: newPassword }) }); setAccess(""); setAccount(null); setPassword(""); setNewPassword(""); setNotice("Password changed. Sign in with your new password."); }); }}>
          <label>Current password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required maxLength={128} autoComplete="current-password" /></label>
          <label>New password<input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required minLength={12} maxLength={128} autoComplete="new-password" /></label>
          <p>Use 12–128 characters with a letter and a number. Changing your password signs out all sessions.</p>
          <button className="btn-secondary" disabled={busy}>Change password</button>
        </form>
      </section>
    </>}
  </div>;
}
