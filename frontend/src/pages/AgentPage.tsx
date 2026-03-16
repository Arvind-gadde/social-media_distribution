import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles, RefreshCw, TrendingUp, Newspaper, Zap, Copy, Check,
  ExternalLink, ChevronDown, ChevronUp, Twitter, Linkedin,
  Instagram, Youtube, Filter, Clock, Star, Hash,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  getAgentFeed, getAgentStats, generateContent, triggerCollection,
  type ContentItem, type GeneratedPost,
} from "../api/agent";

const CATEGORY_META: Record<string, { label: string; dot: string }> = {
  model_release:  { label: "Model Release",  dot: "bg-purple-400" },
  research_paper: { label: "Research",        dot: "bg-blue-400" },
  product_launch: { label: "Product Launch",  dot: "bg-green-400" },
  funding:        { label: "Funding",          dot: "bg-yellow-400" },
  opinion_take:   { label: "Opinion",          dot: "bg-orange-400" },
  tutorial:       { label: "Tutorial",         dot: "bg-teal-400" },
  industry_news:  { label: "Industry News",   dot: "bg-slate-400" },
  open_source:    { label: "Open Source",     dot: "bg-emerald-400" },
  policy_safety:  { label: "Policy/Safety",   dot: "bg-red-400" },
  other:          { label: "Other",            dot: "bg-gray-500" },
};

const PLATFORM_CONFIG = [
  { key: "instagram",      label: "Instagram",     icon: Instagram, accent: "hover:border-pink-500 hover:text-pink-400",  active: "border-pink-500 text-pink-400 bg-pink-500/10" },
  { key: "linkedin",       label: "LinkedIn",      icon: Linkedin,  accent: "hover:border-blue-400 hover:text-blue-400",  active: "border-blue-400 text-blue-400 bg-blue-500/10" },
  { key: "twitter_thread", label: "X Thread",      icon: Twitter,   accent: "hover:border-sky-400 hover:text-sky-300",    active: "border-sky-400 text-sky-300 bg-sky-400/10" },
  { key: "youtube_script", label: "YouTube/Reels", icon: Youtube,   accent: "hover:border-red-500 hover:text-red-400",    active: "border-red-500 text-red-400 bg-red-500/10" },
];

const TIME_OPTIONS = [
  { label: "24h",    value: 24 },
  { label: "48h",    value: 48 },
  { label: "3 days", value: 72 },
  { label: "7 days", value: 168 },
];

const PAGE_SIZE = 15;

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 3600)  return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

function ScoreBar({ score }: { score: number }) {
  const w = Math.round(score * 100);
  const color = score >= 0.8 ? "bg-emerald-400" : score >= 0.6 ? "bg-amber-400" : "bg-slate-600";
  return (
    <div className="flex items-center gap-2 shrink-0">
      <div className="w-14 h-1 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${w}%` }} />
      </div>
      <span className="text-xs text-slate-500 w-7">{w}%</span>
    </div>
  );
}

function CopyBtn({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); toast.success("Copied!"); setTimeout(() => setCopied(false), 2000); }}
      className="flex items-center gap-1 text-xs px-2.5 py-1 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-white transition-all shrink-0"
    >
      {copied ? <Check size={11} /> : <Copy size={11} />}
      {copied ? "Done" : label}
    </button>
  );
}

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: number; color: string }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={17} className="text-white" />
      </div>
      <div>
        <p className="text-xl font-bold text-white">{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </div>
  );
}

function GeneratedPanel({ post, platform }: { post: GeneratedPost; platform: string }) {
  const cfg = PLATFORM_CONFIG.find(p => p.key === platform);
  const Icon = cfg?.icon || Sparkles;
  const [showFull, setShowFull] = useState(false);
  const hashtags = (post.hashtags || []).join(" ");
  const fullText = [post.hook, post.caption, post.call_to_action].filter(Boolean).join("\n\n");

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={14} className="text-slate-400" />
          <span className="text-sm font-semibold text-white">{cfg?.label || platform}</span>
        </div>
        <CopyBtn text={`${fullText}\n\n${hashtags}`} label="Copy all" />
      </div>

      {post.hook && (
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1">Hook</p>
          <p className="text-sm font-semibold text-slate-100 leading-snug">{post.hook}</p>
        </div>
      )}

      {post.caption && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Caption</p>
            <CopyBtn text={post.caption} />
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">
            {showFull ? post.caption : post.caption.slice(0, 280)}
            {post.caption.length > 280 && (
              <button onClick={() => setShowFull(!showFull)} className="ml-1 text-brand-400 hover:text-brand-300 text-xs transition-colors">
                {showFull ? " less" : "...more"}
              </button>
            )}
          </p>
        </div>
      )}

      {platform === "twitter_thread" && post.thread_tweets?.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">
            Thread · {post.thread_tweets.length} tweets
          </p>
          <div className="space-y-2">
            {post.thread_tweets.map((tweet, i) => (
              <div key={i} className="flex gap-2 bg-slate-800 rounded-lg p-2.5">
                <span className="text-xs text-slate-600 w-4 shrink-0 mt-0.5 font-mono">{i + 1}</span>
                <p className="text-sm text-slate-200 flex-1 leading-relaxed">{tweet}</p>
                <CopyBtn text={tweet} />
              </div>
            ))}
          </div>
        </div>
      )}

      {platform === "youtube_script" && post.script_outline && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Script outline</p>
            <CopyBtn text={post.script_outline} />
          </div>
          <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono bg-slate-800 rounded-lg p-3 border border-slate-700 leading-relaxed">
            {post.script_outline}
          </pre>
        </div>
      )}

      {post.hashtags?.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1">
              <Hash size={9} /> {post.hashtags.length} hashtags
            </p>
            <CopyBtn text={hashtags} label="Copy tags" />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {post.hashtags.slice(0, 12).map(tag => (
              <span key={tag} className="text-xs bg-slate-800 border border-slate-700 text-slate-400 px-2 py-0.5 rounded-full">{tag}</span>
            ))}
            {post.hashtags.length > 12 && <span className="text-xs text-slate-600 self-center">+{post.hashtags.length - 12} more</span>}
          </div>
        </div>
      )}

      {post.engagement_tips?.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-1.5">Tips</p>
          <ul className="space-y-1">
            {post.engagement_tips.map((tip, i) => (
              <li key={i} className="text-xs text-slate-400 flex gap-1.5">
                <span className="text-emerald-500 shrink-0">✓</span>{tip}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ContentCard({ item, onGenerate }: {
  item: ContentItem;
  onGenerate: (id: string, platform: string) => Promise<Record<string, GeneratedPost>>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null);
  const [generated, setGenerated] = useState<Record<string, GeneratedPost>>({});
  const meta = CATEGORY_META[item.category] || CATEGORY_META.other;
  const hasGenerated = Object.keys(generated).length > 0;

  const handle = async (platform: string) => {
    setGenerating(platform);
    setExpanded(true);
    try {
      const result = await onGenerate(item.id, platform);
      setGenerated(prev => ({ ...prev, ...result }));
    } finally {
      setGenerating(null);
    }
  };

  return (
    <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl overflow-hidden hover:border-slate-600 hover:bg-slate-800/80 transition-all duration-200">
      <div className="p-5">
        {/* Meta */}
        <div className="flex items-center gap-2 mb-2.5 flex-wrap">
          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${meta.dot}`} />
          <span className="text-xs text-slate-400 font-medium">{meta.label}</span>
          <span className="text-slate-600">·</span>
          <span className="text-xs text-slate-500">{item.source_label}</span>
          <span className="text-slate-600">·</span>
          <span className="text-xs text-slate-500">{timeAgo(item.published_at || item.fetched_at)}</span>
          {item.is_trending && (
            <span className="ml-auto inline-flex items-center gap-1 text-xs text-amber-400 bg-amber-400/10 border border-amber-400/20 px-2 py-0.5 rounded-full font-medium">
              <TrendingUp size={9} /> Trending
            </span>
          )}
        </div>

        {/* Title + score */}
        <div className="flex items-start gap-3 mb-2">
          {item.source_url ? (
            <a href={item.source_url} target="_blank" rel="noopener noreferrer"
              className="text-sm font-semibold text-slate-100 hover:text-white leading-snug group flex items-start gap-1.5 flex-1 transition-colors">
              {item.title}
              <ExternalLink size={11} className="shrink-0 mt-0.5 text-slate-600 group-hover:text-slate-400 transition-colors" />
            </a>
          ) : (
            <p className="text-sm font-semibold text-slate-100 leading-snug flex-1">{item.title}</p>
          )}
          <ScoreBar score={item.relevance_score} />
        </div>

        {item.summary && (
          <p className="text-xs text-slate-500 leading-relaxed line-clamp-2 mb-3">{item.summary}</p>
        )}

        {item.key_points?.length > 0 && (
          <ul className="mb-3 space-y-0.5">
            {item.key_points.slice(0, 2).map((pt, i) => (
              <li key={i} className="text-xs text-slate-500 flex gap-1.5">
                <span className="text-brand-500 shrink-0">›</span>{pt}
              </li>
            ))}
          </ul>
        )}

        {/* Buttons */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-xs text-slate-600 font-medium">Generate:</span>
          {PLATFORM_CONFIG.map(p => (
            <button key={p.key} onClick={() => handle(p.key)} disabled={!!generating}
              className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border font-medium transition-all
                ${generated[p.key] ? p.active : `border-slate-700 text-slate-400 bg-slate-800/80 ${p.accent}`}
                disabled:opacity-40 disabled:cursor-wait`}>
              <p.icon size={11} />
              {generating === p.key ? "..." : p.label}
            </button>
          ))}
          <button onClick={() => handle("all")} disabled={!!generating}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg text-white font-medium transition-all disabled:opacity-40 disabled:cursor-wait"
            style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}>
            <Sparkles size={11} />
            {generating === "all" ? "Generating..." : "All platforms"}
          </button>
          {hasGenerated && (
            <button onClick={() => setExpanded(!expanded)}
              className="ml-auto flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors">
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? "Hide" : "View"}
            </button>
          )}
        </div>
      </div>

      {expanded && hasGenerated && (
        <div className="border-t border-slate-700/60 p-4 bg-slate-900/50 space-y-3">
          {PLATFORM_CONFIG.filter(p => generated[p.key]).map(p => (
            <GeneratedPanel key={p.key} post={generated[p.key]} platform={p.key} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function AgentPage() {
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [hoursBack, setHoursBack] = useState(48);
  const [page, setPage] = useState(0);

  const { data: statsData } = useQuery({
    queryKey: ["agent-stats"],
    queryFn: () => getAgentStats().then(r => r.data),
    refetchInterval: 30_000,
  });

  const { data: feedData, isLoading, isFetching } = useQuery({
    queryKey: ["agent-feed", selectedCategory, hoursBack, page],
    queryFn: () => getAgentFeed({
      category: selectedCategory || undefined,
      hours_back: hoursBack,
      min_score: 0,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }).then(r => r.data),
    placeholderData: (prev) => prev,
  });

  const items = feedData?.items || [];
  const total = feedData?.total || 0;
  const hasMore = (page + 1) * PAGE_SIZE < total;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const categories = feedData?.categories || [];

  const triggerMut = useMutation({
    mutationFn: () => triggerCollection().then(r => r.data),
    onSuccess: () => {
      toast.success("Collecting! Stories appear in ~1 minute.");
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["agent-feed"] });
        queryClient.invalidateQueries({ queryKey: ["agent-stats"] });
      }, 60_000);
    },
    onError: () => toast.error("Failed. Check backend logs."),
  });

  const generateMut = useMutation({
    mutationFn: ({ id, platform }: { id: string; platform: string }) =>
      generateContent(id, platform).then(r => r.data),
    onSuccess: (data) => {
      toast.success(`Generated for ${data.platforms_generated.length} platform(s)!`);
      queryClient.invalidateQueries({ queryKey: ["agent-stats"] });
    },
    onError: () => toast.error("Generation failed. Check OPENAI_API_KEY."),
  });

  const handleGenerate = useCallback(async (id: string, platform: string) => {
    const data = await generateMut.mutateAsync({ id, platform });
    return data.generated;
  }, [generateMut]);

  return (
    <div className="min-h-screen bg-slate-900 animate-fade-in">

      {/* Sticky header */}
      <div className="sticky top-0 z-10 border-b border-slate-800 bg-slate-900/90 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0" style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}>
                <Sparkles size={15} className="text-white" />
              </div>
              Content Intelligence
            </h1>
            <p className="text-xs text-slate-500 mt-0.5 ml-10">AI-curated tech news → ready-to-post · free sources only</p>
          </div>
          <button onClick={() => triggerMut.mutate()} disabled={triggerMut.isPending}
            className="flex items-center gap-2 text-sm px-4 py-2 rounded-xl font-semibold text-white transition-all disabled:opacity-50"
            style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}>
            <RefreshCw size={13} className={triggerMut.isPending ? "animate-spin" : ""} />
            {triggerMut.isPending ? "Collecting..." : "Collect now"}
          </button>
        </div>

        {statsData && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            <StatCard icon={Newspaper}  label="Collected (24h)"     value={statsData.items_collected_24h}  color="bg-brand-600" />
            <StatCard icon={Star}       label="Top stories"          value={statsData.top_stories_24h}      color="bg-purple-600" />
            <StatCard icon={TrendingUp} label="Trending now"         value={statsData.trending_now}          color="bg-amber-600" />
            <StatCard icon={Zap}        label="Content created (7d)" value={statsData.content_generated_7d} color="bg-emerald-600" />
          </div>
        )}
      </div>

      <div className="p-6 space-y-4">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 mr-1">
            <Filter size={12} /> Filter:
          </div>
          <button onClick={() => { setSelectedCategory(null); setPage(0); }}
            className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-all
              ${!selectedCategory ? "bg-brand-600 border-brand-600 text-white" : "border-slate-700 text-slate-400 bg-slate-800 hover:border-slate-500 hover:text-slate-300"}`}>
            All {total > 0 && `(${total})`}
          </button>
          {categories.map(cat => (
            <button key={cat} onClick={() => { setSelectedCategory(cat === selectedCategory ? null : cat); setPage(0); }}
              className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-all flex items-center gap-1.5
                ${selectedCategory === cat ? "bg-brand-600 border-brand-600 text-white" : "border-slate-700 text-slate-400 bg-slate-800 hover:border-slate-500 hover:text-slate-300"}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${CATEGORY_META[cat]?.dot || "bg-gray-500"}`} />
              {CATEGORY_META[cat]?.label || cat}
            </button>
          ))}
          <div className="ml-auto flex items-center gap-2">
            <Clock size={12} className="text-slate-500" />
            <div className="flex rounded-xl overflow-hidden border border-slate-700">
              {TIME_OPTIONS.map(opt => (
                <button key={opt.value} onClick={() => { setHoursBack(opt.value); setPage(0); }}
                  className={`text-xs px-3 py-1.5 font-medium transition-all border-r border-slate-700 last:border-r-0
                    ${hoursBack === opt.value ? "bg-brand-600 text-white" : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"}`}>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {total > 0 && !isLoading && (
          <p className="text-xs text-slate-600">
            {Math.min((page + 1) * PAGE_SIZE, total)} of {total} stories
            {selectedCategory && ` · ${CATEGORY_META[selectedCategory]?.label}`}
          </p>
        )}

        {isLoading && page === 0 ? (
          <div className="space-y-3">
            {[1,2,3].map(i => (
              <div key={i} className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-5 animate-pulse space-y-3">
                <div className="flex gap-2"><div className="h-2 bg-slate-700 rounded w-16" /><div className="h-2 bg-slate-700 rounded w-24" /></div>
                <div className="h-4 bg-slate-700 rounded w-2/3" />
                <div className="h-3 bg-slate-700/50 rounded w-full" />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-16 text-center">
            <Newspaper size={40} className="text-slate-700 mx-auto mb-3" />
            <h3 className="text-slate-400 font-semibold mb-1">
              {selectedCategory ? `No "${CATEGORY_META[selectedCategory]?.label}" stories` : "No stories yet"}
            </h3>
            <p className="text-sm text-slate-600 mb-5">
              {selectedCategory ? "Try a different filter or time range." : "Click Collect now to fetch from 50+ free sources."}
            </p>
            {!selectedCategory && (
              <button onClick={() => triggerMut.mutate()}
                className="text-sm px-5 py-2.5 rounded-xl font-semibold text-white"
                style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}>
                Start collecting
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="space-y-3">
              {items.map(item => (
                <ContentCard key={item.id} item={item} onGenerate={handleGenerate} />
              ))}
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
                  className="text-sm px-4 py-2 rounded-xl border border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                  ← Prev
                </button>
                <span className="text-sm text-slate-500">
                  Page {page + 1} of {totalPages}
                </span>
                <button onClick={() => setPage(p => p + 1)} disabled={!hasMore || isFetching}
                  className="flex items-center gap-2 text-sm px-4 py-2 rounded-xl text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                  style={{ background: "#4f54e5" }}>
                  {isFetching && <RefreshCw size={12} className="animate-spin" />}
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}