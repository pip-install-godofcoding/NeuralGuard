import { createClient } from "@/lib/supabase-server";
import StatsCard from "@/components/StatsCard";
import QueryTable from "@/components/QueryTable";
import CostChart from "@/components/CostChart";

export const revalidate = 30; // ISR: revalidate every 30s

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

async function getMetrics(userId: string) {
  const supabase = await createClient();

  const { data: logs } = await supabase
    .from("query_logs")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(200);

  const allLogs: QueryLog[] = logs ?? [];
  const recentLogs = allLogs.slice(0, 50);

  const totalQueries = allLogs.length;
  const totalCostUsd = allLogs.reduce((s, r) => s + (r.cost_usd ?? 0), 0);
  const totalSavedUsd = allLogs.reduce((s, r) => s + (r.cost_saved_usd ?? 0), 0);
  const cacheHits = allLogs.filter((r) => r.cache_hit).length;
  const cacheHitRate =
    totalQueries > 0 ? (cacheHits / totalQueries) * 100 : 0;

  // Group by day for the chart (last 14 days)
  const byDay: Record<string, { queries: number; saved: number }> = {};
  allLogs.forEach((r) => {
    const day = r.created_at.slice(0, 10);
    if (!byDay[day]) byDay[day] = { queries: 0, saved: 0 };
    byDay[day].queries += 1;
    byDay[day].saved += r.cost_saved_usd ?? 0;
  });
  const chartData = Object.entries(byDay)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-14)
    .map(([date, vals]) => ({ date, ...vals }));

  return {
    totalQueries,
    totalCostUsd,
    totalSavedUsd,
    cacheHitRate,
    recentLogs,
    chartData,
  };
}

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const metrics = await getMetrics(user!.id);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Overview</h1>
        <p className="text-slate-400 text-sm mt-1 font-medium">
          Real-time cost savings and query analytics
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          id="stat-total-queries"
          label="Total Queries"
          value={metrics.totalQueries.toLocaleString()}
          Icon="queries"
          color="indigo"
        />
        <StatsCard
          id="stat-cost-saved"
          label="Total Cost Saved"
          value={`$${metrics.totalSavedUsd.toFixed(4)}`}
          Icon="savings"
          color="emerald"
          highlight
        />
        <StatsCard
          id="stat-cost-incurred"
          label="Cost Incurred"
          value={`$${metrics.totalCostUsd.toFixed(4)}`}
          Icon="cost"
          color="amber"
        />
        <StatsCard
          id="stat-cache-rate"
          label="Cache Hit Rate"
          value={`${metrics.cacheHitRate.toFixed(1)}%`}
          Icon="cache"
          color="purple"
        />
      </div>

      {/* Chart */}
      <div className="glass rounded-2xl p-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-[80px] -mr-32 -mt-32 pointer-events-none" />
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
          Query Volume &amp; Savings — Last 14 Days
        </h2>
        <CostChart data={metrics.chartData} />
      </div>

      {/* Query table */}
      <div className="glass rounded-2xl p-6 relative overflow-hidden">
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-[80px] -ml-32 -mb-32 pointer-events-none" />
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
          Recent Queries
        </h2>
        <QueryTable logs={metrics.recentLogs} />
      </div>
    </div>
  );
}
