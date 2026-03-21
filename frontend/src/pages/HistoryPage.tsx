import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { ChevronDown, ChevronUp, RefreshCw, Trash2, History } from "lucide-react";
import { deletePost, listPosts, retryPost } from "../api/posts";
import { PLATFORMS } from "../types";

const STATUS_BADGE: Record<string, string> = {
  published:  "badge-green",
  partial:    "badge-yellow",
  failed:     "badge-red",
  processing: "badge-blue",
  scheduled:  "badge-purple",
  draft:      "badge-gray",
};

const MEDIA_PILL: Record<string, { label: string; color: string }> = {
  video: { label: "VID", color: "text-blue-300 bg-blue-500/15" },
  image: { label: "IMG", color: "text-emerald-300 bg-emerald-500/15" },
  text:  { label: "TXT", color: "text-purple-300 bg-purple-500/15" },
};

export default function HistoryPage() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data: posts = [], isLoading } = useQuery({
    queryKey: ["posts"],
    queryFn: () => listPosts({ limit: 50 }).then((r) => r.data),
    refetchInterval: 10_000,
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => retryPost(id),
    onSuccess: () => {
      toast.success("Retrying failed platforms");
      queryClient.invalidateQueries({ queryKey: ["posts"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePost(id),
    onSuccess: () => {
      toast.success("Post deleted");
      queryClient.invalidateQueries({ queryKey: ["posts"] });
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-3 animate-fade-in">
        <div className="flex flex-col gap-1 pt-1 mb-5">
          <div className="skeleton h-8 w-40" />
          <div className="skeleton h-4 w-24 mt-1" />
        </div>
        {[1, 2, 3].map((id) => (
          <div key={id} className="skeleton h-[68px] rounded-2xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-3 pt-1 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold text-white tracking-tight">Post History</h1>
          <p className="text-sm text-white/50">All your distributed content</p>
        </div>
        <span className="badge border border-white/10 bg-white/[0.06]">
          {posts.length} posts
        </span>
      </div>

      {posts.length === 0 ? (
        <div className="card py-20 text-center space-y-3">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white/[0.05]">
            <History size={22} className="text-white/20" />
          </div>
          <p className="text-sm font-medium text-white/50">No posts yet</p>
          <p className="text-xs text-white/30">Your published and scheduled posts will appear here.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {posts.map((post, i) => {
            const isOpen = expanded === post.id;
            const hasFailures = Object.values(post.platform_status).some((s) => s.startsWith("failed"));
            const platformList = PLATFORMS.filter((p) => post.target_platforms.includes(p.id));
            const mediaKey = post.media_type === "video" ? "video" : post.media_type === "image" ? "image" : "text";
            const mediaMeta = MEDIA_PILL[mediaKey] || MEDIA_PILL.text;

            return (
              <div
                key={post.id}
                className="glass-card overflow-hidden transition-all duration-200"
                style={{ animationDelay: `${i * 30}ms` }}
              >
                {/* Row header */}
                <button
                  type="button"
                  onClick={() => setExpanded(isOpen ? null : post.id)}
                  className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-white/[0.04] tap-target"
                >
                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[10px] font-bold ${mediaMeta.color}`}>
                    {mediaMeta.label}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-white">
                      {post.caption || post.title || "Untitled"}
                    </p>
                    <p className="text-xs text-white/40 mt-0.5">
                      {format(new Date(post.created_at), "dd MMM yyyy, h:mm a")}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className={`${STATUS_BADGE[post.status] || "badge-gray"} hidden sm:inline-flex`}>
                      {post.status}
                    </span>
                    <span className={`${STATUS_BADGE[post.status] || "badge-gray"} sm:hidden`}>
                      {post.status.slice(0, 3)}
                    </span>
                    {isOpen
                      ? <ChevronUp size={15} className="text-white/35" />
                      : <ChevronDown size={15} className="text-white/35" />
                    }
                  </div>
                </button>

                {/* Expanded details */}
                {isOpen && (
                  <div className="border-t border-white/[0.08] px-5 py-4 space-y-4 animate-fade-in">
                    {/* Platform statuses */}
                    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {platformList.map((platform) => {
                        const status = post.platform_status[platform.id] || "pending";
                        const statusKey = status.startsWith("failed") ? "failed" : status;
                        return (
                          <div
                            key={platform.id}
                            className="flex items-center justify-between rounded-xl bg-white/[0.04] border border-white/[0.06] px-3 py-2.5"
                          >
                            <span className="flex items-center gap-2 text-sm text-white/70">
                              <span className="text-base">{platform.icon}</span>
                              <span className="font-medium">{platform.name}</span>
                            </span>
                            <span className={STATUS_BADGE[statusKey] || "badge-gray"}>
                              {status.startsWith("failed") ? "failed" : status}
                            </span>
                          </div>
                        );
                      })}
                    </div>

                    {/* Caption preview */}
                    {post.caption && (
                      <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-3.5">
                        <p className="text-xs text-white/40 uppercase tracking-wide font-semibold mb-1.5">Caption</p>
                        <p className="text-sm text-white/70 leading-relaxed">{post.caption}</p>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex flex-wrap gap-2">
                      {hasFailures && (
                        <button
                          type="button"
                          onClick={() => retryMutation.mutate(post.id)}
                          disabled={retryMutation.isPending}
                          className="btn-primary px-4 py-2 text-xs"
                        >
                          <RefreshCw size={13} /> Retry Failed
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => { if (confirm("Delete this post?")) deleteMutation.mutate(post.id); }}
                        className="btn-danger px-4 py-2 text-xs"
                      >
                        <Trash2 size={13} /> Delete
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
