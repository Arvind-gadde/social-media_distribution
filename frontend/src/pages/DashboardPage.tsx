import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { AlertCircle, Clock, Send, TrendingUp, ArrowRight } from "lucide-react";
import { getAnalytics } from "../api/analytics";
import { listPosts } from "../api/posts";
import { useAuthStore } from "../store/authStore";
import { PLATFORMS } from "../types";

const STATUS_BADGE: Record<string, string> = {
  published:  "badge-green",
  partial:    "badge-yellow",
  failed:     "badge-red",
  processing: "badge-blue",
  scheduled:  "badge-purple",
  draft:      "badge-gray",
};

const MEDIA_LABELS: Record<string, { label: string; color: string }> = {
  video: { label: "VID", color: "text-blue-300 bg-blue-500/15" },
  image: { label: "IMG", color: "text-emerald-300 bg-emerald-500/15" },
  text:  { label: "TXT", color: "text-purple-300 bg-purple-500/15" },
};

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const { data: analytics } = useQuery({
    queryKey: ["analytics"],
    queryFn: () => getAnalytics().then((response) => response.data),
  });
  const { data: posts = [] } = useQuery({
    queryKey: ["posts"],
    queryFn: () => listPosts({ limit: 5 }).then((response) => response.data),
  });

  const hour = new Date().getHours();
  const greeting = hour < 5 ? "Good night" : hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  const stats = [
    {
      label: "Total Posts",
      value: analytics?.total_posts ?? "—",
      icon: Send,
      iconBg: "bg-brand-600/20",
      iconColor: "text-brand-300",
      trend: null,
    },
    {
      label: "Published",
      value: analytics?.published_posts ?? "—",
      icon: TrendingUp,
      iconBg: "bg-emerald-500/15",
      iconColor: "text-emerald-300",
      trend: null,
    },
    {
      label: "Partial",
      value: analytics?.partial_posts ?? "—",
      icon: AlertCircle,
      iconBg: "bg-amber-500/15",
      iconColor: "text-amber-300",
      trend: null,
    },
    {
      label: "Failed",
      value: analytics?.failed_posts ?? "—",
      icon: Clock,
      iconBg: "bg-red-500/15",
      iconColor: "text-red-300",
      trend: null,
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Header */}
      <header className="flex flex-col gap-1 pt-1">
        <h1 className="text-2xl font-bold text-white tracking-tight">
          {greeting},{" "}
          <span className="gradient-text">{user?.name?.split(" ")[0]}</span> 👋
        </h1>
        <p className="text-sm text-white/50">
          Here's your content pipeline overview.
        </p>
      </header>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, iconBg, iconColor }, index) => (
          <div
            key={label}
            className="card p-5 motion-pop"
            style={{ animationDelay: `${index * 55}ms` }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className={`flex h-10 w-10 items-center justify-center rounded-xl shrink-0 ${iconBg}`}>
                <Icon size={18} className={iconColor} strokeWidth={1.8} />
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-white leading-none">{value}</p>
                <p className="mt-1 text-xs text-white/45 font-medium">{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Connected Platforms */}
      <div className="card">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Connected Platforms</h2>
            <p className="text-xs text-white/40 mt-0.5">Your active distribution channels</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {PLATFORMS.map((platform) => {
            const connected = user?.connected_platforms?.includes(platform.id);
            return (
              <div
                key={platform.id}
                className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold transition-all duration-200 ${
                  connected
                    ? "border-white/15 bg-white/10 text-white"
                    : "border-white/[0.07] bg-white/[0.03] text-white/40"
                }`}
              >
                <span className="text-sm">{platform.icon}</span>
                <span>{platform.name}</span>
                {connected && (
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse-soft" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Posts */}
      <div className="card">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-white">Recent Posts</h2>
            <p className="text-xs text-white/40 mt-0.5">Latest activity</p>
          </div>
          {posts.length > 0 && (
            <a
              href="/history"
              className="flex items-center gap-1 text-xs font-medium text-brand-300 hover:text-brand-200 transition-colors"
            >
              View all <ArrowRight size={12} />
            </a>
          )}
        </div>

        {posts.length === 0 ? (
          <div className="py-14 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5">
              <Send size={22} className="text-white/20" />
            </div>
            <p className="text-sm font-medium text-white/50">No posts yet</p>
            <p className="mt-1 text-xs text-white/30">
              Upload your first piece of content to get started.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {posts.map((post, i) => {
              const mediaKey = post.media_type === "video" ? "video" : post.media_type === "image" ? "image" : "text";
              const mediaMeta = MEDIA_LABELS[mediaKey] || MEDIA_LABELS.text;
              return (
                <div
                  key={post.id}
                  className="flex items-center gap-3 rounded-xl bg-white/[0.04] px-4 py-3 transition-all duration-200 hover:bg-white/[0.07]"
                  style={{ animationDelay: `${i * 40}ms` }}
                >
                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[10px] font-bold ${mediaMeta.color}`}>
                    {mediaMeta.label}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-white">
                      {post.caption || post.title || "Untitled"}
                    </p>
                    <p className="text-xs text-white/40 mt-0.5">
                      {format(new Date(post.created_at), "dd MMM yyyy, h:mm a")}
                    </p>
                  </div>
                  <span className={`${STATUS_BADGE[post.status] || "badge-gray"} shrink-0`}>
                    {post.status}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
