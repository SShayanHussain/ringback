"use client";

import { useRef, useState } from "react";

type Msg = { role: "user" | "agent" | "meta"; text: string };

export default function Playground() {
  const [messages, setMessages] = useState<Msg[]>([
    { role: "agent", text: "Thanks for calling Ringback Home Services. How can I help?" },
  ]);
  const [input, setInput] = useState("");
  const [state, setState] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || busy) return;
    setMessages((m) => [...m, { role: "user", text: message }]);
    setInput("");
    setBusy(true);
    try {
      const res = await fetch("/api/playground", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, state }),
      });
      const raw = await res.text();
      let data: any;
      try { data = JSON.parse(raw); } catch { data = { error: { message: raw } }; }
      if (data.error) {
        setMessages((m) => [...m, { role: "meta", text: `error: ${data.error.message}` }]);
      } else {
        setState(data.state);
        setMessages((m) => [
          ...m,
          { role: "agent", text: data.reply },
          { role: "meta", text: `intent=${data.meta?.intent} outcome=${data.meta?.outcome}${data.meta?.escalated ? " ESCALATED" : ""}` },
        ]);
      }
    } catch (err: any) {
      setMessages((m) => [...m, { role: "meta", text: `network error: ${err.message}` }]);
    } finally {
      setBusy(false);
      requestAnimationFrame(() => logRef.current?.scrollTo(0, logRef.current.scrollHeight));
    }
  }

  function reset() {
    setState(null);
    setMessages([{ role: "agent", text: "Thanks for calling Ringback Home Services. How can I help?" }]);
  }

  return (
    <div>
      <div className="rb-page-title">
        <h1>Playground <span className="rb-muted" style={{ fontSize: ".8rem" }}>text mode · free</span></h1>
        <button className="rb-btn rb-btn-ghost" onClick={reset}>Reset</button>
      </div>

      <div className="rb-card rb-chat">
        <div className="rb-chat-log" ref={logRef}>
          {messages.map((m, i) =>
            m.role === "meta" ? (
              <div key={i} className="rb-msg-meta">{m.text}</div>
            ) : (
              <div key={i} className={`rb-msg ${m.role === "user" ? "rb-msg-user" : "rb-msg-agent"}`}>{m.text}</div>
            )
          )}
        </div>
        <form className="rb-chat-input" onSubmit={send}>
          <input
            className="rb-input"
            placeholder="e.g. I need to book a drain cleaning"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
            autoFocus
          />
          <button className="rb-btn rb-btn-primary" type="submit" disabled={busy}>
            {busy ? "…" : "Send"}
          </button>
        </form>
      </div>
      <p className="rb-muted rb-mt" style={{ fontSize: ".85rem" }}>
        This exercises the exact agent core voice will use — no minutes spent. Try booking, then ask
        for a time that isn&apos;t offered, or say &quot;let me talk to a human&quot;.
      </p>
    </div>
  );
}
