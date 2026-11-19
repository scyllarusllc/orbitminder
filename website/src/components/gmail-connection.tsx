"use client";

import { useEffect, useState } from "react";

type Connection = {
  configured: boolean;
  connected: boolean;
  account_email?: string | null;
  scope?: string;
};
export default function GmailConnection() {
  const [connection, setConnection] = useState<Connection | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  async function load() {
    try {
      const response = await fetch("/api/gmail/connection", { cache: "no-store" });
      const data: Connection = await response.json();
      setConnection(data);
      if (!response.ok) setNote("Gmail connection is not configured on this server.");
    } catch {
      setNote("Gmail connection status is unavailable.");
    }
  }
  useEffect(() => { void load(); }, []);

  async function connect() {
    setBusy(true);
    setNote("");
    try {
      const response = await fetch("/api/gmail/connect", { method: "POST" });
      const body = await response.json() as { authorization_url?: string };
      if (!response.ok || !body.authorization_url) throw new Error("Connection unavailable");
      const url = new URL(body.authorization_url);
      if (url.origin !== "https://accounts.google.com") throw new Error("Invalid authorization URL");
      window.location.assign(url.href);
    } catch {
      setNote("Unable to start Gmail consent. Verify server OAuth configuration.");
      setBusy(false);
    }
  }
  async function disconnect() {
    if (!window.confirm("Disconnect Gmail and remove its locally saved credentials?")) return;
    setBusy(true);
    try {
      const response = await fetch("/api/gmail/connection", { method: "DELETE" });
      if (!response.ok) throw new Error("Disconnect failed");
      setNote("Local Gmail credentials removed. Google revocation may require confirmation in your Google Account.");
      await load();
    } catch {
      setNote("Could not confirm disconnect.");
    } finally {
      setBusy(false);
    }
  }
  return <section className="mt-10 rounded-2xl border border-white/15 bg-white/[0.04] p-6">
    <h2 className="text-xl font-semibold">Gmail connection</h2>
    <p className="mt-1 text-sm text-slate-400">Separate consent · read-only metadata (message IDs and headers) · no sending or deleting</p>
    <p className="mt-4 text-sm text-slate-200">
      {connection?.connected ? `Connected: ${connection.account_email}` :
        connection?.configured ? "Not connected" : "Not configured or still checking"}
    </p>
    <div className="mt-4 flex flex-wrap gap-3">
      {connection?.configured && !connection.connected &&
        <button type="button" onClick={() => void connect()} disabled={busy}
          className="rounded-xl bg-cyan-300 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50">
          Connect Gmail (read only)
        </button>}
      {connection?.connected &&
        <button type="button" onClick={() => void disconnect()} disabled={busy}
          className="rounded-xl border border-white/30 px-4 py-2 disabled:opacity-50">
          Disconnect Gmail
        </button>}
      <button type="button" onClick={() => void load()} disabled={busy}
        className="rounded-xl border border-white/30 px-4 py-2 disabled:opacity-50">Refresh status</button>
    </div>
    {note && <p role="status" className="mt-3 text-sm text-amber-200">{note}</p>}
    <p className="mt-4 text-xs text-slate-400">Connection alone does not start mailbox synchronization. Google OAuth setup and real-account verification are still required.</p>
  </section>;
}
