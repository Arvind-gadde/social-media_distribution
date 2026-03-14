import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listPosts, retryPost, deletePost } from "../api/posts";
import { PLATFORMS } from "../types";
import { format } from "date-fns";
import toast from "react-hot-toast";
import clsx from "clsx";
import { ChevronDown, ChevronUp, RefreshCw, Trash2 } from "lucide-react";

const STATUS_BADGE: Record<string, string> = {
  published: "badge-green", partial: "badge-yellow", failed: "badge-red",
  processing: "badge-blue", scheduled: "badge-purple", draft: "badge-gray",
};

export default function HistoryPage() {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data: posts = [], isLoading } = useQuery({
    queryKey: ["posts"],
    queryFn: () => listPosts({ limit: 50 }).then(r => r.data),
    refetchInterval: 10_000,
  });

  const retryMut = useMutation({
    mutationFn: (id: string) => retryPost(id),
    onSuccess: (_, id) => { toast.success("Retrying failed platforms…"); qc.invalidateQueries({ queryKey: ["posts"] }); },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deletePost(id),
    onSuccess: () => { toast.success("Post deleted"); qc.invalidateQueries({ queryKey: ["posts"] }); },
  });

  if (isLoading) return (
    <div className="p-6 space-y-3">
      {[1,2,3].map(i => <div key={i} className="card h-20 animate-pulse" />)}
    </div>
  );

  return (
    <div className="p-6 space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Post History</h1>
        <span className="text-sm text-slate-400">{posts.length} posts</span>
      </div>

      {posts.length === 0 ? (
        <div className="card py-20 text-center text-slate-400">
          <div className="text-5xl mb-3">📭</div>
          <p className="font-medium">No posts yet</p>
        </div>
      ) : (
        posts.map((post) => {
          const isOpen = expanded === post.id;
          const hasFailures = Object.values(post.platform_status).some(s => s.startsWith("failed"));
          const platformList = PLATFORMS.filter(p => post.target_platforms.includes(p.id));

          return (
            <div key={post.id} className="card overflow-hidden">
              <div onClick={() => setExpanded(isOpen ? null : post.id)}
                className="px-5 py-4 flex items-center gap-3 cursor-pointer hover:bg-slate-50 transition-colors">
                <div className="w-11 h-11 bg-slate-100 rounded-xl flex items-center justify-center text-xl shrink-0">
                  {post.media_type === "video" ? "🎥" : post.media_type === "image" ? "📷" : "📝"}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-700 truncate">{post.caption || post.title || "Untitled"}</p>
                  <p className="text-xs text-slate-400">{format(new Date(post.created_at), "dd MMM yyyy, h:mm a")}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={STATUS_BADGE[post.status] || "badge-gray"}>{post.status}</span>
                  {isOpen ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
                </div>
              </div>

              {isOpen && (
                <div className="border-t border-slate-100 px-5 py-4 space-y-4 animate-fade-in">
                  <div className="grid grid-cols-2 gap-2">
                    {platformList.map((p) => {
                      const s = post.platform_status[p.id] || "pending";
                      const styleKey = s.startsWith("failed") ? "failed" : s;
                      return (
                        <div key={p.id} className="flex items-center justify-between bg-slate-50 rounded-xl px-3 py-2">
                          <span className="text-sm flex items-center gap-1.5">{p.icon} {p.name}</span>
                          <span className={STATUS_BADGE[styleKey] || "badge-gray"}>{s.startsWith("failed") ? "failed" : s}</span>
                        </div>
                      );
                    })}
                  </div>
                  {post.caption && (
                    <p className="text-sm text-slate-600 bg-slate-50 rounded-xl p-3">{post.caption}</p>
                  )}
                  <div className="flex gap-2">
                    {hasFailures && (
                      <button onClick={() => retryMut.mutate(post.id)} disabled={retryMut.isPending}
                        className="btn-primary text-sm py-2 px-4 flex items-center gap-2">
                        <RefreshCw size={14} /> Retry Failed
                      </button>
                    )}
                    <button onClick={() => { if (confirm("Delete this post?")) deleteMut.mutate(post.id); }}
                      className="btn-danger text-sm py-2 px-4 flex items-center gap-2">
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