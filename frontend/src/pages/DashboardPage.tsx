import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { AlertCircle, Clock, Send, TrendingUp } from "lucide-react";
import { getAnalytics } from "../api/analytics";
import { listPosts } from "../api/posts";
import { useAuthStore } from "../store/authStore";
import { PLATFORMS } from "../types";

const STATUS_BADGE: Record<string, string> = {
  published: "badge-green",
  partial: "badge-yellow",
  failed: "badge-red",
  processing: "badge-blue",
  scheduled: "badge-purple",
  draft: "badge-gray",
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

  const stats = [
    {
      label: "Total Posts",
      value: analytics?.total_posts ?? "-",
      icon: Send,
      color: "text-brand-300",
      bg: "bg-white/10",
    },
    {
      label: "Published",
      value: analytics?.published_posts ?? "-",
      icon: TrendingUp,
      color: "text-emerald-300",
      bg: "bg-white/10",
    },
    {
      label: "Partial",
      value: analytics?.partial_posts ?? "-",
      icon: AlertCircle,
      color: "text-amber-300",
      bg: "bg-white/10",
    },
    {
      label: "Failed",
      value: analytics?.failed_posts ?? "-",
      icon: Clock,
      color: "text-red-300",
      bg: "bg-white/10",
    },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold text-white">
          Good {new Date().getHours() < 12 ? "morning" : "evening"},{" "}
          {user?.name?.split(" ")[0]}
        </h1>
        <p className="text-white/60">
          A quick overview of your content pipeline and performance metrics.
        </p>
      </header>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="card p-5">
            <div className="flex items-center justify-between gap-4">
              <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${bg}`}>
                <Icon size={20} className={color} />
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-white">{value}</p>
                <p className="text-xs text-white/50">{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Connected Platforms</h2>
          <p className="text-xs text-white/50">Sync status updates in real time</p>
        </div>
        <div className="flex flex-wrap gap-3">
          {PLATFORMS.map((platform) => {
            const connected = user?.connected_platforms?.includes(platform.id);
            return (
              <div
                key={platform.id}
                className={
                  "flex items-center gap-2 rounded-2xl border px-4 py-2 text-sm font-semibold transition " +
                  (connected
                    ? "border-white/10 bg-white/10 text-white"
                    : "border-white/10 bg-white/5 text-white/60")
                }
              >
                <span>{platform.icon}</span>
                <span>{platform.name}</span>
                {connected && <span className="h-2 w-2 rounded-full bg-emerald-400" />}
              </div>
            );
          })}
        </div>
      </div>

      <div className="card p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Recent Posts</h2>
          <p className="text-xs text-white/50">Latest activity</p>
        </div>

        {posts.length === 0 ? (
          <div className="py-16 text-center text-white/50">
            <p className="text-base font-medium text-white/70">No posts yet</p>
            <p className="mt-2 text-sm text-white/45">
              Upload your first piece of content to get started.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {posts.map((post) => (
              <div
                key={post.id}
                className="flex items-center gap-4 rounded-2xl bg-white/5 p-4 transition hover:bg-white/10"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-lg">
                  {post.media_type === "video" ? "VID" : post.media_type === "image" ? "IMG" : "TXT"}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-white">
                    {post.caption || post.title || "Untitled"}
                  </p>
                  <p className="text-xs text-white/50">
                    {format(new Date(post.created_at), "dd MMM yyyy, h:mm a")}
                  </p>
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
