"use client";

import { useState } from "react";

interface Key {
  id: string;
  label: string;
  is_active: boolean;
  created_at: string;
  revoked_at: string | null;
}

export default function ApiKeyManager({
  userId,
  initialKeys,
}: {
  userId: string;
  initialKeys: Key[];
}) {
  const [keys, setKeys] = useState<Key[]>(initialKeys);
  const [newKeyPlaintext, setNewKeyPlaintext] = useState<string | null>(null);
  const [label, setLabel] = useState("My Key");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  async function createKey() {
    setLoading(true);
    setError("");
    setNewKeyPlaintext(null);

    try {
      const res = await fetch("/api/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ label }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Failed to create key");

      setNewKeyPlaintext(data.key);
      setKeys((prev) => [
        { ...data.meta, is_active: true, revoked_at: null },
        ...prev,
      ]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  function copyKey() {
    if (!newKeyPlaintext) return;
    navigator.clipboard.writeText(newKeyPlaintext);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-6">
      {/* Create key form */}
      <div className="glass rounded-2xl p-6 space-y-4">
        <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">
          Create New Key
        </h3>
        <div className="flex gap-3">
          <input
            id="key-label-input"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Key label"
            className="flex-1 bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/40 transition-all font-medium"
          />
          <button
            id="create-key-btn"
            onClick={createKey}
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium px-5 py-2.5 rounded-xl transition-all duration-200 hover:shadow-lg hover:shadow-indigo-500/20 whitespace-nowrap"
          >
            {loading ? "Creating…" : "Create Key"}
          </button>
        </div>

        {error && (
          <p className="text-red-400 text-sm">{error}</p>
        )}

        {/* Reveal new key once */}
        {newKeyPlaintext && (
          <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4">
            <p className="text-xs text-emerald-400/60 mb-2 font-medium uppercase tracking-wider">
              ⚠ Copy this key — it will not be shown again
            </p>
            <div className="flex items-center gap-3">
              <code className="flex-1 font-mono text-sm text-emerald-400 break-all">
                {newKeyPlaintext}
              </code>
              <button
                id="copy-key-btn"
                onClick={copyKey}
                className="shrink-0 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 text-xs font-medium px-3 py-1.5 rounded-lg transition-all border border-emerald-500/20"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <p className="text-xs text-white/30 mt-3">
              Use this as your <code className="font-mono">api_key</code> with{" "}
              <code className="font-mono">base_url=&quot;{process.env.NEXT_PUBLIC_PROXY_URL}/v1&quot;</code>
            </p>
          </div>
        )}
      </div>

      {/* Existing keys */}
      <div className="glass rounded-2xl overflow-hidden mt-6">
        <div className="px-6 py-4 border-b border-slate-800">
          <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">
            Your Keys
          </h3>
        </div>
        {keys.length === 0 ? (
          <p className="text-slate-400 font-medium text-sm text-center py-8">No keys yet.</p>
        ) : (
          <ul className="divide-y divide-slate-800/50">
            {keys.map((k) => (
              <li key={k.id} className="flex items-center justify-between px-6 py-4 gap-4 hover:bg-slate-800/30 transition-colors">
                <div>
                  <p className="text-sm font-semibold text-slate-200">{k.label}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Created {new Date(k.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span
                  className={`text-xs font-semibold px-2.5 py-1 rounded-lg border ${
                    k.is_active
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : "bg-slate-800/50 text-slate-500 border-slate-700/50"
                  }`}
                >
                  {k.is_active ? "Active" : "Revoked"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
