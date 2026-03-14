import { useQuery } from "@tanstack/react-query";
import { getAnalytics } from "../api/analytics";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";
import { PLATFORMS } from "../types";

const COLORS = ["#6272f1","#a855f7","#f472b6","#34d399","#f59e0b","#60a5fa","#f87171","#a3e635","#fb923c","#38bdf8","#c084fc","#4ade80"];

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: () => getAnalytics().then(r => r.data),
  });

  if (isLoading) return <div className="p-6"><div className="card h-64 animate-pulse" /></div>;
  if (!data) return null;

  const distData = Object.entries(data.platform_distribution).map(([key, val]) => ({
    name: PLATFORMS.find(p => p.id === key)?.name ?? key,
    posts: val,
  }));

  const successData = Object.entries(data.platform_success_rate).map(([key, val]) => ({
    name: PLATFORMS.find(p => p.id === key)?.name ?? key,
    rate: val,
  }));

  const pieData = distData;

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-slate-800">Analytics</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total",     val: data.total_posts,     color: "text-brand-600" },
          { label: "Published", val: data.published_posts,  color: "text-emerald-600" },
          { label: "Partial",   val: data.partial_posts,   color: "text-amber-600" },
          { label: "Failed",    val: data.failed_posts,    color: "text-red-500" },
        ].map(({ label, val, color }) => (
          <div key={label} className="card p-5 text-center">
            <p className={`text-3xl font-bold ${color}`}>{val}</p>
            <p className="text-sm text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Distribution Bar */}
        <div className="card p-5">
          <h2 className="font-semibold text-slate-700 mb-4">Posts per Platform</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={distData}>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="posts" fill="#6272f1" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie */}
        <div className="card p-5">
          <h2 className="font-semibold text-slate-700 mb-4">Distribution Share</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} dataKey="posts" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Success Rate */}
        <div className="card p-5 lg:col-span-2">
          <h2 className="font-semibold text-slate-700 mb-4">Success Rate by Platform (%)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={successData}>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis domain={[0,100]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => `${v}%`} />
              <Bar dataKey="rate" fill="#34d399" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}