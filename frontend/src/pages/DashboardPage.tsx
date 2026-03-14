import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "../store/authStore";
import { getAnalytics } from "../api/analytics";
import { listPosts } from "../api/posts";
import { format } from "date-fns";
import { TrendingUp, Send, AlertCircle, Clock } from "lucide-react";
import { PLATFORMS } from "../types";
import clsx from "clsx";

const STATUS_BADGE: Record<string, string> = {
  published: "badge-green",
  partial:   "badge-yellow",
  failed:    "badge-red",
  processing:"badge-blue",
  scheduled: "badge-purple",
  draft:     "badge-gray",
};

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const { data: analytics } = useQuery({ queryKey: ["analytics"], queryFn: () => getAnalytics().then(r => r.data) });
  const { data: posts = [] } = useQuery({ queryKey: ["posts"], queryFn: () => listPosts({ limit: 5 }).then(r => r.data) });

  const stats = [
    { label: "Total Posts",     value: analytics?.total_posts     ?? "—", icon: Send,         color: "text-brand-600", bg: "bg-brand-50"  },
    { label: "Published",       value: analytics?.published_posts  ?? "—", icon: TrendingUp,   color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Partial",         value: analytics?.partial_posts   ?? "—", icon: AlertCircle,  color: "text-amber-600",   bg: "bg-amber-50"  },
    { label: "Failed",          value: analytics?.failed_posts    ?? "—", icon: Clock,        color: "text-red-600",    bg: "bg-red-50"    },
  ];

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">
          Good {new Date().getHours() < 12 ? "morning" : "evening"}, {user?.name?.split(" ")[0]} 👋
        </h1>
        <p className="text-slate-500 text-sm mt-1">Here's how your content is performing</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="card p-5 flex items-center gap-4">
            <div className={clsx("w-11 h-11 rounded-xl flex items-center justify-center", bg)}>
              <Icon size={20} className={color} />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800">{value}</p>
              <p className="text-xs text-slate-500">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Connected Platforms */}
      <div className="card p-5">
        <h2 className="font-semibold text-slate-700 mb-4">Connected Platforms</h2>
        <div className="flex flex-wrap gap-2">
          {PLATFORMS.map((p) => {
            const connected = user?.connected_platforms?.includes(p.id);
            return (
              <div key={p.id} className={clsx(
                "flex items-center gap-2 px-3 py-1.5 rounded-xl border text-sm font-medium",
                connected ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-100 bg-slate-50 text-slate-400"
              )}>
                <span>{p.icon}</span>
                <span>{p.name}</span>
                {connected && <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />}
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Posts */}
      <div className="card">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-700">Recent Posts</h2>
        </div>
        {posts.length === 0 ? (
          <div className="py-12 text-center text-slate-400">
            <div className="text-4xl mb-2">📭</div>
            <p>No posts yet — go upload your first piece of content!</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-50">
            {posts.map((post) => (
              <div key={post.id} className="px-5 py-3.5 flex items-center gap-3 hover:bg-slate-50 transition-colors">
                <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center text-lg shrink-0">
                  {post.media_type === "video" ? "🎥" : post.media_type === "image" ? "📷" : "📝"}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-700 truncate">{post.caption || post.title || "Untitled"}</p>
                  <p className="text-xs text-slate-400">{format(new Date(post.created_at), "dd MMM yyyy, h:mm a")}</p>
                </div>
                <span className={STATUS_BADGE[post.status] || "badge-gray"}>{post.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}