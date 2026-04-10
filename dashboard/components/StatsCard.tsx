type Color = "indigo" | "emerald" | "amber" | "purple";
type IconType = "queries" | "savings" | "cost" | "cache";

const COLOR_MAP: Record<Color, { bg: string; text: string; glow: string; border: string }> = {
  indigo:  { bg: "bg-indigo-500/10",  text: "text-indigo-400",  glow: "glow-indigo",  border: "border-indigo-500/20"  },
  emerald: { bg: "bg-emerald-500/10", text: "text-emerald-400", glow: "glow-emerald", border: "border-emerald-500/20" },
  amber:   { bg: "bg-amber-500/10",   text: "text-amber-400",   glow: "glow-amber",   border: "border-amber-500/20"   },
  purple:  { bg: "bg-purple-500/10",  text: "text-purple-400",  glow: "",             border: "border-purple-500/20"  },
};

function IconComponent({ type, className }: { type: IconType; className: string }) {
  switch (type) {
    case "queries":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.501 48.172 48.172 0 003.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
        </svg>
      );
    case "savings":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
    case "cost":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 004.5 19.5z" />
        </svg>
      );
    case "cache":
      return (
        <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
        </svg>
      );
  }
}

interface Props {
  id: string;
  label: string;
  value: string;
  Icon: IconType;
  color: Color;
  highlight?: boolean;
}

export default function StatsCard({ id, label, value, Icon, color, highlight }: Props) {
  const c = COLOR_MAP[color];

  return (
    <div
      id={id}
      className={`glass rounded-2xl p-5 ${c.glow} border ${c.border} transition-all duration-300 hover:scale-[1.02] ${highlight ? "ring-1 ring-emerald-500/20" : ""}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</p>
          <p className={`text-2xl font-bold mt-1.5 ${highlight ? "text-emerald-400" : "text-slate-50"}`}>
            {value}
          </p>
        </div>
        <div className={`w-10 h-10 rounded-xl ${c.bg} flex items-center justify-center shrink-0`}>
          <IconComponent type={Icon} className={`w-5 h-5 ${c.text}`} />
        </div>
      </div>
    </div>
  );
}
