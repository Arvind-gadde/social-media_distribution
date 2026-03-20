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
    <div className="flex items-center gap-1.5 shrink-0">
      <div className="w-12 h-1 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${w}%` }} />
      </div>
      <span className="text-[10px] text-white/40 w-6 tabular-nums">{w}%</span>
    </div>
  );
}

function CopyBtn({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        toast.success("Copied!");
        setTimeout(() => setCopied(false), 2000);
      }}
      className="flex items-center gap-1 text-[11px] px-2 py-1 rounded-lg bg-white/[0.07] hover:bg-white/15 text-white/50 hover:text-white transition-all shrink-0"
    >
      {copied ? <Check size={10} /> : <Copy size={10} />}
      {copied ? "Done" : label}
    </button>
  );
}

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: number; color: string }) {
  return (
    <div className="glass rounded-2xl p-4 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${color} shrink-0`}>
        <Icon size={16} className="text-white" />
      </div>
      <div>
        <p className="text-xl font-bold text-white leading-none">{value}</p>
        <p className="text-[11px] text-white/40 mt-0.5">{label}</p>
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
    <div className="border border-white/[0.09] bg-white/[0.03] rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={13} className="text-white/50" />
          <span className="text-sm font-semibold text-white">{cfg?.label || platform}</span>
        </div>
        <CopyBtn text={`${fullText}\n\n${hashtags}`} label="Copy all" />
      </div>

      {post.hook && (
        <div>
          <p className="text-[10px] font-semibold text-white/35 uppercase tracking-wider mb-1">Hook</p>
          <p className="text-sm font-semibold text-white leading-snug">{post.hook}</p>
        </div>
      )}

      {post.caption && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-[10px] font-semibold text-white/35 uppercase tracking-wider">Caption</p>
            <CopyBtn text={post.caption} />
          </div>
          <p className="text-sm text-white/70 leading-relaxed">
            {showFull ? post.caption : post.caption.slice(0, 280)}
            {post.caption.length > 280 && (
              <button onClick={() => setShowFull(!showFull)} className="ml-1 text-brand-300 hover:text-brand-200 text-xs transition-colors">
                {showFull ? " less" : "…more"}
              </button>
            )}
          </p>
        </div>
      )}

      {platform === "twitter_thread" && post.thread_tweets?.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-white/35 uppercase tracking-wider mb-2">
            Thread · {post.thread_tweets.length} tweets
          </p>
          <div className="space-y-1.5">
            {post.thread_tweets.map((tweet, i) => (
              <div key={i} className="flex gap-2 bg-white/[0.04] rounded-lg p-2.5">
                <span className="text-[11px] text-white/30 w-4 shrink-0 mt-0.5 font-mono">{i + 1}</span>
                <p className="text-sm text-white/80 flex-1 leading-relaxed">{tweet}</p>
                <CopyBtn text={tweet} />
              </div>
            ))}
          </div>
        </div>
      )}

      {platform === "youtube_script" && post.script_outline && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <p className="text-[10px] font-semibold text-white/35 uppercase tracking-wider">Script outline</p>
            <CopyBtn text={post.script_outline} />
          </div>
          <pre className="text-xs text-white/60 whitespace-pre-wrap font-mono bg-white/[0.04] rounded-xl p-3 border border-white/[0.07] leading-relaxed text-wrap">
            {post.script_outline}
          </pre>
        </div>
      )}

      {post.hashtags?.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <p className="text-[10px] font-semibold text-white/35 uppercase tracking-wider flex items-center gap-1">
              <Hash size={9} /> {post.hashtags.length} hashtags
            </p>
            <CopyBtn text={hashtags} label="Copy tags" />
          </div>
          <div className="flex flex-wrap gap-1">
            {post.hashtags.slice(0, 12).map(tag => (
              <span key={tag} className="text-[10px] bg-white/[0.06] border border-white/[0.08] text-white/50 px-2 py-0.5 rounded-full">{tag}</span>
            ))}
            {post.hashtags.length > 12 && <span className="text-[11px] text-white/30 self-center">+{post.hashtags.length - 12}</span>}
          </div>
        </div>
      )}

      {post.engagement_tips?.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-white/35 uppercase tracking-wider mb-1.5">Tips</p>
          <ul className="space-y-1">
            {post.engagement_tips.map((tip, i) => (
              <li key={i} className="text-xs text-white/55 flex gap-1.5">
                <span className="text-emerald-400 shrink-0">✓</span>{tip}
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
    <div className="glass-card overflow-hidden hover:border-white/[0.15] transition-all duration-200 p-0">
      <div className="p-5">
        {/* Meta row */}
        <div className="flex items-center gap-2 mb-2.5 flex-wrap">
          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${meta.dot}`} />
          <span className="text-xs text-white/50 font-medium">{meta.label}</span>
          <span className="text-white/20">·</span>
          <span className="text-xs text-white/40">{item.source_label}</span>
          <span className="text-white/20">·</span>
          <span className="text-xs text-white/40">{timeAgo(item.published_at || item.fetched_at)}</span>
          {item.is_trending && (
            <span className="ml-auto inline-flex items-center gap-1 text-[10px] text-amber-300 bg-amber-400/10 border border-amber-400/20 px-2 py-0.5 rounded-full font-semibold">
              <TrendingUp size={9} /> Trending
            </span>
          )}
        </div>

        {/* Title + score */}
        <div className="flex items-start gap-3 mb-2.5">
          {item.source_url ? (
            <a href={item.source_url} target="_blank" rel="noopener noreferrer"
              className="text-sm font-semibold text-white hover:text-white/90 leading-snug group flex items-start gap-1.5 flex-1 transition-colors">
              {item.title}
              <ExternalLink size={11} className="shrink-0 mt-0.5 text-white/25 group-hover:text-white/55 transition-colors" />
            </a>
          ) : (
            <p className="text-sm font-semibold text-white leading-snug flex-1">{item.title}</p>
          )}
          <ScoreBar score={item.relevance_score} />
        </div>

        {item.summary && (
          <p className="text-xs text-white/45 leading-relaxed line-clamp-2 mb-3">{item.summary}</p>
        )}

        {item.key_points?.length > 0 && (
          <ul className="mb-3 space-y-0.5">
            {item.key_points.slice(0, 2).map((pt, i) => (
              <li key={i} className="text-xs text-white/45 flex gap-1.5">
                <span className="text-brand-400 shrink-0">›</span>{pt}
              </li>
            ))}
          </ul>
        )}

        {/* Generate buttons */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[11px] text-white/30 font-medium mr-0.5">Generate:</span>
          {PLATFORM_CONFIG.map(p => (
            <button key={p.key} onClick={() => handle(p.key)} disabled={!!generating}
              className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg border font-semibold transition-all
                ${generated[p.key] ? p.active : `border-white/[0.09] text-white/50 bg-white/[0.04] ${p.accent}`}
                disabled:opacity-40 disabled:cursor-wait`}>
              <p.icon size={11} />
              {generating === p.key ? "…" : p.label}
            </button>
          ))}
          <button onClick={() => handle("all")} disabled={!!generating}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg text-white font-semibold transition-all disabled:opacity-40 disabled:cursor-wait"
            style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}>
            <Sparkles size={11} />
            {generating === "all" ? "Generating…" : "All platforms"}
          </button>
          {hasGenerated && (
            <button onClick={() => setExpanded(!expanded)}
              className="ml-auto flex items-center gap-1 text-xs text-brand-300 hover:text-brand-200 transition-colors">
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? "Hide" : "View"}
            </button>
          )}
        </div>
      </div>

      {expanded && hasGenerated && (
        <div className="border-t border-white/[0.07] p-4 bg-white/[0.02] space-y-3 animate-fade-in">
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
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-1 pt-1 mb-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0" style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}>
                <Sparkles size={15} className="text-white" />
              </div>
              Content Intelligence
            </h1>
            <p className="text-sm text-white/45 mt-1 ml-10">AI-curated tech news → ready-to-post · free sources only</p>
          </div>
          <button
            onClick={() => triggerMut.mutate()}
            disabled={triggerMut.isPending}
            className="flex items-center gap-2 text-sm px-4 py-2.5 rounded-xl font-semibold text-white transition-all disabled:opacity-50"
            style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}
          >
            <RefreshCw size={13} className={triggerMut.isPending ? "animate-spin" : ""} />
            {triggerMut.isPending ? "Collecting…" : "Collect now"}
          </button>
        </div>

        {/* Stats */}
        {statsData && (
          <div className="grid grid-cols-2 gap-2 mt-3 sm:grid-cols-4">
            <StatCard icon={Newspaper}  label="Collected (24h)"     value={statsData.items_collected_24h}  color="bg-brand-600/70" />
            <StatCard icon={Star}       label="Top stories"          value={statsData.top_stories_24h}      color="bg-purple-600/70" />
            <StatCard icon={TrendingUp} label="Trending now"         value={statsData.trending_now}          color="bg-amber-600/70" />
            <StatCard icon={Zap}        label="Content created (7d)" value={statsData.content_generated_7d} color="bg-emerald-600/70" />
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <div className="flex items-center gap-1 text-xs text-white/35">
          <Filter size={11} /> Filter:
        </div>
        <button
          onClick={() => { setSelectedCategory(null); setPage(0); }}
          className={`text-xs px-3 py-1.5 rounded-full border font-semibold transition-all
            ${!selectedCategory ? "bg-brand-600 border-brand-600 text-white" : "border-white/[0.09] text-white/50 bg-white/[0.04] hover:border-white/20 hover:text-white"}`}
        >
          All {total > 0 && `(${total})`}
        </button>
        {categories.map(cat => (
          <button key={cat}
            onClick={() => { setSelectedCategory(cat === selectedCategory ? null : cat); setPage(0); }}
            className={`text-xs px-3 py-1.5 rounded-full border font-semibold transition-all flex items-center gap-1.5
              ${selectedCategory === cat ? "bg-brand-600 border-brand-600 text-white" : "border-white/[0.09] text-white/50 bg-white/[0.04] hover:border-white/20 hover:text-white"}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${CATEGORY_META[cat]?.dot || "bg-gray-500"}`} />
            {CATEGORY_META[cat]?.label || cat}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <Clock size={11} className="text-white/35" />
          <div className="flex rounded-xl overflow-hidden border border-white/[0.09]">
            {TIME_OPTIONS.map(opt => (
              <button key={opt.value}
                onClick={() => { setHoursBack(opt.value); setPage(0); }}
                className={`text-xs px-3 py-1.5 font-semibold transition-all border-r border-white/[0.09] last:border-r-0
                  ${hoursBack === opt.value ? "bg-brand-600 text-white" : "bg-white/[0.04] text-white/45 hover:bg-white/[0.08] hover:text-white"}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {total > 0 && !isLoading && (
        <p className="text-xs text-white/30 mb-3">
          {Math.min((page + 1) * PAGE_SIZE, total)} of {total} stories
          {selectedCategory && ` · ${CATEGORY_META[selectedCategory]?.label}`}
        </p>
      )}

      {/* Content */}
      {isLoading && page === 0 ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="glass-card p-5 animate-pulse space-y-3">
              <div className="flex gap-2"><div className="skeleton h-2 w-16" /><div className="skeleton h-2 w-24" /></div>
              <div className="skeleton h-4 w-2/3" />
              <div className="skeleton h-3 w-full opacity-60" />
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="card py-20 text-center space-y-3">
          <Newspaper size={36} className="text-white/15 mx-auto" />
          <h3 className="text-sm font-semibold text-white/50">
            {selectedCategory ? `No "${CATEGORY_META[selectedCategory]?.label}" stories` : "No stories yet"}
          </h3>
          <p className="text-xs text-white/30">
            {selectedCategory ? "Try a different filter or time range." : "Click Collect now to fetch from 50+ free sources."}
          </p>
          {!selectedCategory && (
            <button onClick={() => triggerMut.mutate()}
              className="text-sm px-5 py-2.5 rounded-xl font-semibold text-white mt-2"
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
            <div className="flex items-center justify-between pt-4">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="text-sm px-4 py-2 rounded-xl border border-white/[0.09] text-white/50 hover:bg-white/[0.07] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                ← Prev
              </button>
              <span className="text-sm text-white/40">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={!hasMore || isFetching}
                className="flex items-center gap-2 text-sm px-4 py-2 rounded-xl text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                style={{ background: "linear-gradient(135deg,#4f54e5,#7c3aed)" }}
              >
                {isFetching && <RefreshCw size={12} className="animate-spin" />}
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
