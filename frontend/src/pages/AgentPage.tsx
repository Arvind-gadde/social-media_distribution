import { useState, useCallback, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles, RefreshCw, TrendingUp, Newspaper, Zap, Copy, Check,
  ExternalLink, ChevronDown, ChevronUp, Twitter, Linkedin,
  Instagram, Youtube, Filter, Clock, Star, Hash,
  ShieldCheck, ShieldAlert, ShieldQuestion, Flame, X,
  Github, Globe, MessageSquare, BookOpen,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  getAgentFeed, getAgentStats, generateContent, triggerCollection,
  type ContentItem, type GeneratedPost, type SourceType,
} from "../api/agent";
import { OverviewModal } from "../components/ui/OverviewModal";
import { hasApiResponse } from "../lib/apiErrors";

// ─── Constants ────────────────────────────────────────────────────────────────

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

const SOURCE_TYPE_CONFIG: Record<string, { label: string; icon: typeof Globe; color: string }> = {
  x:          { label: "𝕏 / Twitter",  icon: Twitter,       color: "text-sky-400" },
  linkedin:   { label: "LinkedIn",     icon: Linkedin,      color: "text-blue-400" },
  rss:        { label: "RSS",          icon: Globe,         color: "text-orange-400" },
  github:     { label: "GitHub",       icon: Github,        color: "text-white/70" },
  reddit:     { label: "Reddit",       icon: MessageSquare, color: "text-orange-500" },
  hackernews: { label: "Hacker News",  icon: Zap,           color: "text-amber-400" },
  youtube:    { label: "YouTube",      icon: Youtube,       color: "text-red-400" },
};

const TIME_OPTIONS = [
  { label: "24h",    value: 24 },
  { label: "48h",    value: 48 },
  { label: "3 days", value: 72 },
  { label: "7 days", value: 168 },
];

const PAGE_SIZE = 15;
const NEW_ITEMS_KEY = "contentflow_agent_last_seen_total";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 3600)  return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

// ─── Virality Ring ────────────────────────────────────────────────────────────

function ViralityRing({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const r = 16;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const color = pct >= 70 ? "#10b981" : pct >= 45 ? "#f59e0b" : "#475569";

  return (
    <div className="relative flex h-10 w-10 shrink-0 items-center justify-center sm:h-11 sm:w-11">
      <svg width="44" height="44" viewBox="0 0 44 44" className="h-10 w-10 -rotate-90 sm:h-11 sm:w-11">
        <circle cx="22" cy="22" r={r} stroke="rgba(255,255,255,0.08)" strokeWidth="3" fill="none" />
        <circle cx="22" cy="22" r={r} stroke={color} strokeWidth="3" fill="none"
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
      </svg>
      <span className="absolute text-[10px] font-bold text-white/80">{pct}</span>
    </div>
  );
}

// ─── Content-Worthy Badge ─────────────────────────────────────────────────────

function ContentWorthyBadge({ virality }: { virality: number }) {
  const pct = Math.round(virality * 100);
  if (pct >= 60) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 font-semibold">
        <Zap size={9} /> Create Content
      </span>
    );
  }
  if (pct >= 40) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-400/25 font-semibold">
        <Zap size={9} /> Maybe
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] text-white/35 border border-white/[0.09] font-semibold">
      <Zap size={9} /> Skip
    </span>
  );
}

// ─── Fact-Check Badge ─────────────────────────────────────────────────────────

function FactBadge({ passed }: { passed: boolean | null }) {
  if (passed === null)
    return <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-white/[0.07] text-white/40 border border-white/[0.09]"><ShieldQuestion size={9} /> Unverified</span>;
  if (passed)
    return <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25"><ShieldCheck size={9} /> Verified</span>;
  return <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/25"><ShieldAlert size={9} /> Flagged</span>;
}

// ─── Sentiment Bar ────────────────────────────────────────────────────────────

function SentimentBar({ breakdown }: { breakdown: Record<string, number> }) {
  const pos = Math.round((breakdown.positive ?? 0) * 100);
  const neg = Math.round((breakdown.negative ?? 0) * 100);
  const con = Math.round((breakdown.controversial ?? 0) * 100);
  if (pos + neg + con === 0) return null;
  return (
    <div className="space-y-0.5">
      <p className="text-[10px] text-white/30 uppercase tracking-wider">Sentiment</p>
      <div className="flex h-1.5 rounded-full overflow-hidden w-24 gap-px">
        {pos > 0 && <div className="bg-emerald-500" style={{ width: `${pos}%` }} />}
        {neg > 0 && <div className="bg-red-500" style={{ width: `${neg}%` }} />}
        {con > 0 && <div className="bg-amber-500" style={{ width: `${con}%` }} />}
      </div>
    </div>
  );
}

// ─── Source Icon ───────────────────────────────────────────────────────────────

function SourceIcon({ sourceType }: { sourceType: string }) {
  const cfg = SOURCE_TYPE_CONFIG[sourceType];
  if (!cfg) return null;
  const Icon = cfg.icon;
  return <Icon size={12} className={`shrink-0 ${cfg.color}`} />;
}

// ─── Copy Button ──────────────────────────────────────────────────────────────

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

// ─── Stat Card ────────────────────────────────────────────────────────────────

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

// ─── Generated Panel ──────────────────────────────────────────────────────────

function GeneratedPanel({ post, platform }: { post: GeneratedPost; platform: string }) {
  const cfg = PLATFORM_CONFIG.find(p => p.key === platform);
  const Icon = cfg?.icon || Sparkles;
  const [showFull, setShowFull] = useState(false);
  const hashtags = (post.hashtags || []).join(" ");
  const fullText = [post.hook, post.caption, post.call_to_action].filter(Boolean).join("\n\n");

  return (
      <div className="border border-white/[0.09] bg-white/[0.03] rounded-xl p-4 space-y-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-2">
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
            <div className="mb-1 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
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
                <div key={i} className="flex flex-col gap-2 rounded-lg bg-white/[0.04] p-2.5 sm:flex-row">
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
            <div className="mb-1 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
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
            <div className="mb-1.5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
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

// ─── Content Card (REDESIGNED) ────────────────────────────────────────────────

function ContentCard({ item, onGenerate, onViewOverview }: {
  item: ContentItem;
  onGenerate: (id: string, platform: string) => Promise<Record<string, GeneratedPost>>;
  onViewOverview: (item: ContentItem) => void;
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
        {/* Row 1: Source + Category + Time + Badges */}
          <div className="mb-3 flex flex-wrap items-start gap-2">
          <SourceIcon sourceType={item.source_type} />
          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${meta.dot}`} />
          <span className="text-xs text-white/50 font-medium">{meta.label}</span>
          <span className="text-white/20">·</span>
          <span className="text-xs text-white/40">{item.source_label}</span>
          <span className="text-white/20">·</span>
          <span className="text-xs text-white/40">{timeAgo(item.published_at || item.fetched_at)}</span>
            <div className="flex w-full flex-wrap items-center gap-1.5 sm:ml-auto sm:w-auto sm:justify-end">
            {item.is_trending && (
              <span className="inline-flex items-center gap-1 text-[10px] text-amber-300 bg-amber-400/10 border border-amber-400/20 px-2 py-0.5 rounded-full font-semibold">
                <TrendingUp size={9} /> Trending
              </span>
            )}
            {item.is_value_gap && (
              <span className="inline-flex items-center gap-1 text-[10px] text-orange-300 bg-orange-500/10 border border-orange-400/20 px-2 py-0.5 rounded-full font-semibold">
                <Flame size={9} /> Gap
              </span>
            )}
            <ContentWorthyBadge virality={item.virality_score} />
            <FactBadge passed={item.fact_check_passed} />
          </div>
        </div>

        {/* Row 2: Virality Ring + Title + Summary */}
        <div className="flex items-start gap-3 mb-3">
          <ViralityRing score={item.virality_score} />
          <div className="flex-1 min-w-0">
            {item.source_url ? (
              <a href={item.source_url} target="_blank" rel="noopener noreferrer"
                className="text-sm font-semibold text-white hover:text-white/90 leading-snug group flex items-start gap-1.5 transition-colors">
                {item.title}
                <ExternalLink size={11} className="shrink-0 mt-0.5 text-white/25 group-hover:text-white/55 transition-colors" />
              </a>
            ) : (
              <p className="text-sm font-semibold text-white leading-snug">{item.title}</p>
            )}

            {item.summary && (
              <p className="text-xs text-white/50 leading-relaxed mt-1.5">{item.summary}</p>
            )}
          </div>
        </div>

        {/* Row 3: Key Points */}
        {item.key_points?.length > 0 && (
            <ul className="mb-3 space-y-0.5 sm:ml-14">
            {item.key_points.slice(0, 3).map((pt, i) => (
              <li key={i} className="text-xs text-white/45 flex gap-1.5">
                <span className="text-brand-400 shrink-0">›</span>{pt}
              </li>
            ))}
            {item.key_points.length > 3 && (
              <li className="text-[10px] text-white/25">+{item.key_points.length - 3} more</li>
            )}
          </ul>
        )}

        {/* Row 4: Suggested angle + Sentiment */}
        {(item.suggested_angle || Object.keys(item.sentiment_breakdown).length > 0) && (
          <div className="mb-3 flex flex-col gap-3 sm:ml-14 sm:flex-row sm:flex-wrap sm:items-end">
            {item.suggested_angle && (
              <div className="flex-1 min-w-0 bg-white/[0.04] border border-white/[0.07] rounded-lg p-2.5">
                <p className="text-[10px] text-white/35 uppercase tracking-wider mb-0.5 flex items-center gap-1">
                  <Zap size={9} /> Suggested angle
                </p>
                <p className="text-xs text-white/70 leading-relaxed">{item.suggested_angle}</p>
              </div>
            )}
            <SentimentBar breakdown={item.sentiment_breakdown} />
          </div>
        )}

        {/* Row 5: Generate buttons */}
        <div className="flex flex-wrap items-stretch gap-1.5 pt-1 sm:ml-14 sm:items-center">
          <button onClick={() => onViewOverview(item)}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-brand-500/30 bg-brand-500/10 px-2.5 py-1.5 text-xs font-semibold text-brand-300 transition-all hover:bg-brand-500/20 sm:mr-2 sm:w-auto">
            <BookOpen size={11} />
            Overview
          </button>
          
          <span className="w-full text-[11px] font-medium text-white/30 sm:mr-0.5 sm:w-auto">Generate:</span>
          {PLATFORM_CONFIG.map(p => (
            <button key={p.key} onClick={() => handle(p.key)} disabled={!!generating}
              className={`flex items-center justify-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-all
                ${generated[p.key] ? p.active : `border-white/[0.09] text-white/50 bg-white/[0.04] ${p.accent}`}
                disabled:opacity-40 disabled:cursor-wait`}>
              <p.icon size={11} />
              {generating === p.key ? "…" : p.label}
            </button>
          ))}
          <button onClick={() => handle("all")} disabled={!!generating}
            className="flex items-center justify-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-white transition-all disabled:cursor-wait disabled:opacity-40"
            style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}>
            <Sparkles size={11} />
            {generating === "all" ? "Generating…" : "All platforms"}
          </button>
          {hasGenerated && (
            <button onClick={() => setExpanded(!expanded)}
              className="flex w-full items-center justify-center gap-1 text-xs text-brand-300 transition-colors hover:text-brand-200 sm:ml-auto sm:w-auto sm:justify-end">
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

// ─── New Items Banner ─────────────────────────────────────────────────────────

function NewItemsBanner({ newCount, onDismiss }: { newCount: number; onDismiss: () => void }) {
  if (newCount <= 0) return null;
  return (
    <div className="relative mb-4 flex flex-col items-start gap-3 overflow-hidden rounded-xl border border-brand-500/30 px-4 py-3 animate-slide-up sm:flex-row sm:items-center sm:justify-between"
      style={{ background: "linear-gradient(135deg, rgba(98,114,241,0.12), rgba(168,85,247,0.12))" }}>
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-brand-500/20 shrink-0">
          <Flame size={15} className="text-brand-300" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">
            🔥 {newCount} new {newCount === 1 ? "story" : "stories"} since your last visit
          </p>
          <p className="text-xs text-white/40">Fresh content opportunities are waiting for you</p>
        </div>
      </div>
      <button
        onClick={onDismiss}
        className="rounded-lg p-1.5 text-white/40 hover:bg-white/10 hover:text-white transition-all shrink-0"
        aria-label="Dismiss"
      >
        <X size={16} />
      </button>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AgentPage() {
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedSourceType, setSelectedSourceType] = useState<string | null>(null);
  const [hoursBack, setHoursBack] = useState(48);
  const [page, setPage] = useState(0);
  const [newItemsCount, setNewItemsCount] = useState(0);
  const [overviewItem, setOverviewItem] = useState<ContentItem | null>(null);
  const bannerDismissedRef = useRef(false);

  const { data: statsData } = useQuery({
    queryKey: ["agent-stats"],
    queryFn: () => getAgentStats().then(r => r.data),
    refetchInterval: 30_000,
  });

  const { data: feedData, isLoading, isFetching } = useQuery({
    queryKey: ["agent-feed", selectedCategory, selectedSourceType, hoursBack, page],
    queryFn: () => getAgentFeed({
      category: selectedCategory || undefined,
      source_type: selectedSourceType || undefined,
      hours_back: hoursBack,
      min_score: 0,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }).then(r => r.data),
    placeholderData: (prev) => prev,
  });

  // Track new items for the banner
  useEffect(() => {
    if (!feedData || bannerDismissedRef.current) return;
    const lastSeen = parseInt(localStorage.getItem(NEW_ITEMS_KEY) || "0", 10);
    if (feedData.total > lastSeen && lastSeen > 0) {
      setNewItemsCount(feedData.total - lastSeen);
    }
  }, [feedData]);

  const handleDismissNewItems = () => {
    if (feedData) {
      localStorage.setItem(NEW_ITEMS_KEY, String(feedData.total));
    }
    setNewItemsCount(0);
    bannerDismissedRef.current = true;
  };

  const items = feedData?.items || [];
  const total = feedData?.total || 0;
  const hasMore = (page + 1) * PAGE_SIZE < total;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const categories = feedData?.categories || [];
  const sourceTypes: SourceType[] = feedData?.source_types || [];

  // Poll after collection to detect new items and show notification
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const baselineRef = useRef(0);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const triggerMut = useMutation({
    mutationFn: () => triggerCollection().then(r => r.data),
    onSuccess: () => {
      toast.success("Pipeline started! Polling for results…");
      baselineRef.current = statsData?.items_collected_24h ?? 0;
      let ticks = 0;
      const MAX_TICKS = 12; // 12 × 10s = 2 min

      stopPolling();
      pollRef.current = setInterval(async () => {
        ticks++;
        try {
          const fresh = await getAgentStats().then(r => r.data);
          if (fresh.items_collected_24h > baselineRef.current) {
            const newCount = fresh.items_collected_24h - baselineRef.current;
            toast.success(`🔥 ${newCount} new stories collected!`);
            setNewItemsCount(newCount);
            bannerDismissedRef.current = false;
            queryClient.invalidateQueries({ queryKey: ["agent-feed"] });
            queryClient.invalidateQueries({ queryKey: ["agent-stats"] });
            stopPolling();
          } else if (ticks >= MAX_TICKS) {
            toast("Collection may still be running — refresh to check.", { icon: "⏱️" });
            queryClient.invalidateQueries({ queryKey: ["agent-feed"] });
            queryClient.invalidateQueries({ queryKey: ["agent-stats"] });
            stopPolling();
          }
        } catch {
          // Polling error — keep going
        }
      }, 10_000);
    },
    onError: (error) => {
      if (!hasApiResponse(error)) {
        toast.error("Failed. Check backend logs.");
      }
    },
  });

  const generateMut = useMutation({
    mutationFn: ({ id, platform }: { id: string; platform: string }) =>
      generateContent(id, platform).then(r => r.data),
    onSuccess: (data) => {
      toast.success(`Generated for ${data.platforms_generated.length} platform(s)!`);
      queryClient.invalidateQueries({ queryKey: ["agent-stats"] });
    },
    onError: (error) => {
      if (!hasApiResponse(error)) {
        toast.error("Generation failed. Check your connection.");
      }
    },
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
            <p className="mt-1 text-sm text-white/45 sm:ml-10">AI-curated tech news → ready-to-post · free sources only</p>
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

      {/* Source-type filter chips */}
      {sourceTypes.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 mb-3">
          <span className="text-[11px] text-white/30 font-medium mr-0.5">Sources:</span>
          <button
            onClick={() => { setSelectedSourceType(null); setPage(0); }}
            className={`text-xs px-3 py-1.5 rounded-full border font-semibold transition-all flex items-center gap-1.5
              ${!selectedSourceType ? "bg-brand-600 border-brand-600 text-white" : "border-white/[0.09] text-white/50 bg-white/[0.04] hover:border-white/20 hover:text-white"}`}
          >
            All
          </button>
          {sourceTypes.map(st => {
            const cfg = SOURCE_TYPE_CONFIG[st];
            if (!cfg) return null;
            const Icon = cfg.icon;
            return (
              <button key={st}
                onClick={() => { setSelectedSourceType(st === selectedSourceType ? null : st); setPage(0); }}
                className={`text-xs px-3 py-1.5 rounded-full border font-semibold transition-all flex items-center gap-1.5
                  ${selectedSourceType === st ? "bg-brand-600 border-brand-600 text-white" : "border-white/[0.09] text-white/50 bg-white/[0.04] hover:border-white/20 hover:text-white"}`}
              >
                <Icon size={11} className={selectedSourceType === st ? "text-white" : cfg.color} />
                {cfg.label}
              </button>
            );
          })}
        </div>
      )}

      {/* Category + time filters */}
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
        <div className="flex w-full items-center gap-2 sm:ml-auto sm:w-auto">
          <Clock size={11} className="text-white/35" />
          <div className="flex flex-1 overflow-x-auto rounded-xl border border-white/[0.09] sm:flex-none">
            {TIME_OPTIONS.map(opt => (
              <button key={opt.value}
                onClick={() => { setHoursBack(opt.value); setPage(0); }}
                className={`shrink-0 border-r border-white/[0.09] px-3 py-1.5 text-xs font-semibold transition-all last:border-r-0
                  ${hoursBack === opt.value ? "bg-brand-600 text-white" : "bg-white/[0.04] text-white/45 hover:bg-white/[0.08] hover:text-white"}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* New items banner */}
      <NewItemsBanner newCount={newItemsCount} onDismiss={handleDismissNewItems} />

      {total > 0 && !isLoading && (
        <p className="text-xs text-white/30 mb-3">
          {Math.min((page + 1) * PAGE_SIZE, total)} of {total} stories
          {selectedCategory && ` · ${CATEGORY_META[selectedCategory]?.label}`}
          {selectedSourceType && ` · ${SOURCE_TYPE_CONFIG[selectedSourceType]?.label}`}
        </p>
      )}

      {/* Content */}
      {isLoading && page === 0 ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="glass-card p-5 animate-pulse space-y-3">
              <div className="flex gap-3"><div className="skeleton w-11 h-11 rounded-full shrink-0" /><div className="flex-1 space-y-2"><div className="skeleton h-2.5 w-3/4" /><div className="skeleton h-2 w-full" /><div className="skeleton h-2 w-2/3 opacity-60" /></div></div>
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
              <ContentCard key={item.id} item={item} onGenerate={handleGenerate} onViewOverview={setOverviewItem} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex flex-col gap-2 pt-4 sm:flex-row sm:items-center sm:justify-between">
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

      {/* Root-Level Overview Modal */}
      {overviewItem && (
        <OverviewModal item={overviewItem} onClose={() => setOverviewItem(null)} />
      )}
    </div>
  );
}
