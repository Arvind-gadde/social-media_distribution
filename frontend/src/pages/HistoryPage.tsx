import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import toast from "react-hot-toast";
import { ChevronDown, ChevronUp, RefreshCw, Trash2 } from "lucide-react";
import { deletePost, listPosts, retryPost } from "../api/posts";
import { PLATFORMS } from "../types";

const STATUS_BADGE: Record<string, string> = {
  published: "badge-green",
  partial: "badge-yellow",
  failed: "badge-red",
  processing: "badge-blue",
  scheduled: "badge-purple",
  draft: "badge-gray",
};

export default function HistoryPage() {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data: posts = [], isLoading } = useQuery({
    queryKey: ["posts"],
    queryFn: () => listPosts({ limit: 50 }).then((response) => response.data),
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
      <div className="space-y-3 p-6">
        {[1, 2, 3].map((id) => (
          <div key={id} className="card h-20 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4 p-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Post History</h1>
        <span className="text-sm text-white/45">{posts.length} posts</span>
      </div>

      {posts.length === 0 ? (
        <div className="card py-20 text-center text-white/50">
          <p className="font-medium">No posts yet</p>
        </div>
      ) : (
        posts.map((post) => {
          const isOpen = expanded === post.id;
          const hasFailures = Object.values(post.platform_status).some((status) =>
            status.startsWith("failed")
          );
          const platformList = PLATFORMS.filter((platform) =>
            post.target_platforms.includes(platform.id)
          );

          return (
            <div key={post.id} className="card overflow-hidden">
              <button
                type="button"
                onClick={() => setExpanded(isOpen ? null : post.id)}
                className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-white/[0.04]"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/10 text-[11px] font-semibold text-white/80">
                  {post.media_type === "video" ? "VID" : post.media_type === "image" ? "IMG" : "TXT"}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-white">
                    {post.caption || post.title || "Untitled"}
                  </p>
                  <p className="text-xs text-white/45">
                    {format(new Date(post.created_at), "dd MMM yyyy, h:mm a")}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className={STATUS_BADGE[post.status] || "badge-gray"}>{post.status}</span>
                  {isOpen ? (
                    <ChevronUp size={16} className="text-white/45" />
                  ) : (
                    <ChevronDown size={16} className="text-white/45" />
                  )}
                </div>
              </button>

              {isOpen && (
                <div className="space-y-4 border-t border-white/10 px-5 py-4 animate-fade-in">
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    {platformList.map((platform) => {
                      const status = post.platform_status[platform.id] || "pending";
                      const statusKey = status.startsWith("failed") ? "failed" : status;
                      return (
                        <div
                          key={platform.id}
                          className="flex items-center justify-between rounded-xl bg-white/[0.04] px-3 py-2"
                        >
                          <span className="flex items-center gap-1.5 text-sm text-white/75">
                            {platform.icon} {platform.name}
                          </span>
                          <span className={STATUS_BADGE[statusKey] || "badge-gray"}>
                            {status.startsWith("failed") ? "failed" : status}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                  {post.caption && (
                    <p className="rounded-xl bg-white/[0.04] p-3 text-sm text-white/70">
                      {post.caption}
                    </p>
                  )}
                  <div className="flex gap-2">
                    {hasFailures && (
                      <button
                        type="button"
                        onClick={() => retryMutation.mutate(post.id)}
                        disabled={retryMutation.isPending}
                        className="btn-primary flex items-center gap-2 px-4 py-2 text-sm"
                      >
                        <RefreshCw size={14} /> Retry Failed
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm("Delete this post?")) deleteMutation.mutate(post.id);
                      }}
                      className="btn-danger flex items-center gap-2 px-4 py-2 text-sm"
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
