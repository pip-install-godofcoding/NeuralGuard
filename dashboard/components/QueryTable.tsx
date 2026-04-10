interface QueryLog {
  id: string;
  model_requested: string;
  model_used: string;
  prompt_snippet: string;
  token_usage: number;
  cost_usd: number;
  cost_saved_usd: number;
  cache_hit: boolean;
  latency_ms: number;
  trust_score: number | null;
  created_at: string;
}

function TrustBadge({ score }: { score: number | null }) {
  if (score === null)
    return <span className="text-slate-500 font-medium text-xs">—</span>;

  const color =
    score >= 80
      ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
      : score >= 60
      ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
      : "bg-red-500/20 text-red-400 border-red-500/30";

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold border ${color}`}>
      {score}
    </span>
  );
}

function CacheHitBadge({ hit }: { hit: boolean }) {
  return hit ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-md text-xs font-medium">
      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
      HIT
    </span>
  ) : (
    <span className="text-slate-500 font-medium text-xs">—</span>
  );
}

export default function QueryTable({ logs }: { logs: QueryLog[] }) {
  if (logs.length === 0) {
    return (
      <p className="text-center text-slate-400 font-medium text-sm py-8">
        No queries yet. Point your app at the NeuralGuard proxy to start.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800">
            {["Prompt", "Requested", "Used", "Tokens", "Cost", "Saved", "Cache", "Trust", "Latency"].map(
              (h) => (
                <th
                  key={h}
                  className="text-left pb-3 pr-4 text-xs font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap"
                >
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/50">
          {logs.map((log) => (
            <tr key={log.id} className="hover:bg-slate-800/30 transition-colors">
              <td className="py-3 pr-4 max-w-[200px] truncate text-slate-200 font-medium" title={log.prompt_snippet}>
                {log.prompt_snippet || "—"}
              </td>
              <td className="py-3 pr-4 text-slate-400 whitespace-nowrap font-mono text-xs">
                {log.model_requested}
              </td>
              <td className="py-3 pr-4 text-slate-300 whitespace-nowrap font-mono text-xs">
                {log.model_used}
              </td>
              <td className="py-3 pr-4 text-slate-400 whitespace-nowrap">
                {log.token_usage ? log.token_usage.toLocaleString() : "—"}
              </td>
              <td className="py-3 pr-4 text-slate-400 whitespace-nowrap font-mono text-xs">
                ${(log.cost_usd ?? 0).toFixed(5)}
              </td>
              <td className="py-3 pr-4 whitespace-nowrap font-mono text-xs">
                <span className={log.cost_saved_usd > 0 ? "text-emerald-400 font-medium" : "text-slate-500 font-medium"}>
                  {log.cost_saved_usd > 0 ? `$${log.cost_saved_usd.toFixed(5)}` : "—"}
                </span>
              </td>
              <td className="py-3 pr-4">
                <CacheHitBadge hit={log.cache_hit} />
              </td>
              <td className="py-3 pr-4">
                <TrustBadge score={log.trust_score} />
              </td>
              <td className="py-3 pr-4 text-slate-400 whitespace-nowrap text-xs">
                {log.latency_ms ? `${Math.round(log.latency_ms)}ms` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
