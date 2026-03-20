import { useQuery } from "@tanstack/react-query";
import {
  Bar, BarChart, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { getAnalytics } from "../api/analytics";
import { PLATFORMS } from "../types";
import { BarChart2, TrendingUp, AlertCircle, CheckCircle } from "lucide-react";

const COLORS = [
  "#8557f5", "#a855f7", "#f472b6", "#34d399",
  "#f59e0b", "#60a5fa", "#f87171", "#a3e635",
  "#fb923c", "#38bdf8", "#c084fc", "#4ade80",
];

const AXIS_TICK = { fill: "rgba(241,245,249,0.45)", fontSize: 11, fontFamily: "Plus Jakarta Sans" };
const TOOLTIP_STYLE = {
  backgroundColor: "rgba(10,12,22,0.96)",
  border: "1px solid rgba(255,255,255,0.10)",
  borderRadius: "12px",
  color: "#f1f5f9",
  fontSize: "12px",
  fontFamily: "Plus Jakarta Sans",
  boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
};

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: () => getAnalytics().then((r) => r.data),
  });

  if (isLoading) {
    return (
      <div className="space-y-5 animate-fade-in">
        <div className="flex flex-col gap-1 pt-1">
          <div className="skeleton h-8 w-36" />
        </div>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[1,2,3,4].map((i) => <div key={i} className="skeleton h-24 rounded-2xl" />)}
        </div>
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="skeleton h-64 rounded-2xl" />
          <div className="skeleton h-64 rounded-2xl" />
        </div>
      </div>
    );
  }
  if (!data) return null;

  const distData = Object.entries(data.platform_distribution).map(([platform, posts]) => ({
    name: PLATFORMS.find((p) => p.id === platform)?.name ?? platform,
    posts,
  }));

  const successData = Object.entries(data.platform_success_rate).map(([platform, rate]) => ({
    name: PLATFORMS.find((p) => p.id === platform)?.name ?? platform,
    rate,
  }));

  const statItems = [
    { label: "Total Posts",  value: data.total_posts,     icon: BarChart2,    color: "text-brand-300",   bg: "bg-brand-500/15"   },
    { label: "Published",    value: data.published_posts, icon: CheckCircle,  color: "text-emerald-300", bg: "bg-emerald-500/15" },
    { label: "Partial",      value: data.partial_posts,   icon: AlertCircle,  color: "text-amber-300",   bg: "bg-amber-500/15"   },
    { label: "Failed",       value: data.failed_posts,    icon: TrendingUp,   color: "text-red-300",     bg: "bg-red-500/15"     },
  ];

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-1 pt-1">
        <h1 className="text-2xl font-bold text-white tracking-tight">Analytics</h1>
        <p className="text-sm text-white/50">Your distribution performance overview</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {statItems.map(({ label, value, icon: Icon, color, bg }, i) => (
          <div key={label} className="card p-5 motion-pop" style={{ animationDelay: `${i * 55}ms` }}>
            <div className="flex items-start justify-between gap-2">
              <div className={`flex h-10 w-10 items-center justify-center rounded-xl shrink-0 ${bg}`}>
                <Icon size={18} className={color} strokeWidth={1.8} />
              </div>
              <div className="text-right">
                <p className={`text-3xl font-bold ${color}`}>{value}</p>
                <p className="mt-1 text-xs text-white/45 font-medium">{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Posts per Platform */}
        <div className="card p-5">
          <h2 className="mb-1 text-sm font-semibold text-white">Posts per Platform</h2>
          <p className="mb-4 text-xs text-white/40">Distribution across channels</p>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={distData} margin={{ left: -10 }}>
              <XAxis dataKey="name" tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
              <Bar dataKey="posts" radius={[6, 6, 0, 0]}>
                {distData.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Distribution Share */}
        <div className="card p-5">
          <h2 className="mb-1 text-sm font-semibold text-white">Distribution Share</h2>
          <p className="mb-4 text-xs text-white/40">Breakdown by platform</p>
          <ResponsiveContainer width="100%" height={210}>
            <PieChart>
              <Pie
                data={distData}
                dataKey="posts"
                nameKey="name"
                cx="50%"
                cy="48%"
                outerRadius={72}
                innerRadius={32}
                paddingAngle={2}
                label
              >
                {distData.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend
                wrapperStyle={{ color: "rgba(241,245,249,0.55)", fontSize: "11px", fontFamily: "Plus Jakarta Sans" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Success Rate */}
        <div className="card p-5 lg:col-span-2">
          <h2 className="mb-1 text-sm font-semibold text-white">Success Rate by Platform</h2>
          <p className="mb-4 text-xs text-white/40">Percentage of successfully published posts</p>
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={successData} margin={{ left: -10 }}>
              <XAxis dataKey="name" tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <Tooltip
                formatter={(value: number) => [`${value}%`, "Success rate"]}
                contentStyle={TOOLTIP_STYLE}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar dataKey="rate" radius={[6, 6, 0, 0]}>
                {successData.map((entry, index) => (
                  <Cell
                    key={index}
                    fill={entry.rate >= 80 ? "#34d399" : entry.rate >= 50 ? "#f59e0b" : "#f87171"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
