import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getAnalytics } from "../api/analytics";
import { PLATFORMS } from "../types";

const COLORS = [
  "#6272f1",
  "#a855f7",
  "#f472b6",
  "#34d399",
  "#f59e0b",
  "#60a5fa",
  "#f87171",
  "#a3e635",
  "#fb923c",
  "#38bdf8",
  "#c084fc",
  "#4ade80",
];

const AXIS_TICK = { fill: "rgba(248, 250, 252, 0.6)", fontSize: 11 };
const TOOLTIP_STYLE = {
  backgroundColor: "rgba(15, 23, 42, 0.96)",
  border: "1px solid rgba(255, 255, 255, 0.12)",
  borderRadius: "16px",
  color: "#f8fafc",
};

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: () => getAnalytics().then((response) => response.data),
  });

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="card h-64 animate-pulse" />
      </div>
    );
  }
  if (!data) return null;

  const distData = Object.entries(data.platform_distribution).map(([platform, posts]) => ({
    name: PLATFORMS.find((item) => item.id === platform)?.name ?? platform,
    posts,
  }));

  const successData = Object.entries(data.platform_success_rate).map(([platform, rate]) => ({
    name: PLATFORMS.find((item) => item.id === platform)?.name ?? platform,
    rate,
  }));

  return (
    <div className="space-y-6 p-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-white">Analytics</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: "Total", value: data.total_posts, color: "text-brand-300" },
          { label: "Published", value: data.published_posts, color: "text-emerald-300" },
          { label: "Partial", value: data.partial_posts, color: "text-amber-300" },
          { label: "Failed", value: data.failed_posts, color: "text-red-300" },
        ].map(({ label, value, color }) => (
          <div key={label} className="card p-5 text-center">
            <p className={`text-3xl font-bold ${color}`}>{value}</p>
            <p className="mt-1 text-sm text-white/50">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="mb-4 font-semibold text-white">Posts per Platform</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={distData}>
              <XAxis dataKey="name" tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar dataKey="posts" fill="#6272f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5">
          <h2 className="mb-4 font-semibold text-white">Distribution Share</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={distData}
                dataKey="posts"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label
              >
                {distData.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend
                wrapperStyle={{
                  color: "rgba(248, 250, 252, 0.7)",
                  fontSize: "12px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5 lg:col-span-2">
          <h2 className="mb-4 font-semibold text-white">Success Rate by Platform (%)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={successData}>
              <XAxis dataKey="name" tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <Tooltip
                formatter={(value: number) => `${value}%`}
                contentStyle={TOOLTIP_STYLE}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar dataKey="rate" fill="#34d399" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
