import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles, RefreshCw, TrendingUp, Newspaper, Zap, Copy, Check,
  ExternalLink, ChevronDown, ChevronUp, Globe, Twitter,
  Linkedin, Instagram, Youtube, Filter, Clock, Star, Hash,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  getAgentFeed, getAgentStats, generateContent, triggerCollection,
  type ContentItem, type GeneratedPost,
} from "../api/agent";

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  model_release:   { label: "Model Release",   color: "bg-purple-100 text-purple-700" },
  research_paper:  { label: "Research",         color: "bg-blue-100 text-blue-700" },
  product_launch:  { label: "Product Launch",   color: "bg-green-100 text-green-700" },
  funding:         { label: "Funding",           color: "bg-yellow-100 text-yellow-800" },
  opinion_take:    { label: "Opinion",           color: "bg-orange-100 text-orange-700" },
  tutorial:        { label: "Tutorial",          color: "bg-teal-100 text-teal-700" },
  industry_news:   { label: "Industry News",    color: "bg-slate-100 text-slate-700" },
  open_source:     { label: "Open Source",      color: "bg-emerald-100 text-emerald-700" },
  policy_safety:   { label: "Policy/Safety",    color: "bg-red-100 text-red-700" },
  other:           { label: "Other",             color: "bg-gray-100 text-gray-600" },
};

const PLATFORM_CONFIG = [
  { key: "instagram",      label: "Instagram",     icon: Instagram,  color: "text-pink-600",   bg: "bg-pink-50 border-pink-200" },
  { key: "linkedin",       label: "LinkedIn",      icon: Linkedin,   color: "text-blue-700",   bg: "bg-blue-50 border-blue-200" },
  { key: "twitter_thread", label: "X Thread",      icon: Twitter,    color: "text-sky-600",    bg: "bg-sky-50 border-sky-200" },
  { key: "youtube_script", label: "YouTube/Reels", icon: Youtube,    color: "text-red-600",    bg: "bg-red-50 border-red-200" },
];

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 3600)  return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

function ScoreBar({ score }: { score: number }) {
  const w = Math.round(score * 100);
  const color = score >= 0.8 ? "bg-emerald-500" : score >= 0.6 ? "bg-amber-500" : "bg-slate-300";
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${w}%` }} />
      </div>
      <span className="text-xs text-slate-400">{w}%</span>
    </div>
  );
}

function CopyBtn({ text, label = "" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        toast.success("Copied!");
        setTimeout(() => setCopied(false), 2000);
      }}
      className="flex items-center gap-1 text-xs px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 transition"
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {label || (copied ? "Copied" : "Copy")}
    </button>
  );
}

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: number | string; color: string }) {
  return (
    <div className="card p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color}`}>
        <Icon size={18} className="text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800">{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </div>
  );
}

function GeneratedPanel({ post, platform }: { post: GeneratedPost; platform: string }) {
  const cfg = PLATFORM_CONFIG.find(p => p.key === platform);
  const Icon = cfg?.icon || Globe;
  const [showFull, setShowFull] = useState(false);
  const hashtags = (post.hashtags || []).join(" ");
  const fullCaption = [post.hook, post.caption, post.call_to_action].filter(Boolean).join("\n\n");

  return (
    <div className={`rounded-xl border p-4 space-y-3 ${cfg?.bg || "bg-slate-50 border-slate-200"}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={16} className={cfg?.color || "text-slate-500"} />
          <span className="text-sm font-semibold text-slate-700">{cfg?.label || platform}</span>
        </div>
        <CopyBtn text={`${fullCaption}\n\n${hashtags}`} label="Copy all" />
      </div>

      {post.hook && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Hook</p>
          <p className="text-sm text-slate-800 font-medium">{post.hook}</p>
        </div>
      )}

      {post.caption && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Caption</p>
            <CopyBtn text={post.caption} />
          </div>
          <div className="text-sm text-slate-700 leading-relaxed">
            {showFull ? post.caption : post.caption.slice(0, 200)}
            {post.caption.length > 200 && (
              <button onClick={() => setShowFull(!showFull)} className="ml-1 text-brand-600 hover:underline text-xs">
                {showFull ? "less" : "...more"}
              </button>
            )}
          </div>
        </div>
      )}

      {platform === "twitter_thread" && post.thread_tweets?.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Thread</p>
          {post.thread_tweets.map((tweet, i) => (
            <div key={i} className="flex gap-2 items-start">
              <span className="text-xs text-slate-400 mt-0.5 w-4 shrink-0">{i + 1}</span>
              <p className="text-sm text-slate-700 flex-1">{tweet}</p>
              <CopyBtn text={tweet} />
            </div>
          ))}
        </div>
      )}

      {platform === "youtube_script" && post.script_outline && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Script outline</p>
            <CopyBtn text={post.script_outline} />
          </div>
          <pre className="text-xs text-slate-700 whitespace-pre-wrap font-sans leading-relaxed bg-white rounded-lg p-3 border border-slate-200">
            {post.script_outline}
          </pre>
        </div>
      )}

      {post.hashtags?.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide flex items-center gap-1">
              <Hash size={10} /> Hashtags ({post.hashtags.length})
            </p>
            <CopyBtn text={hashtags} label="Copy tags" />
          </div>
          <div className="flex flex-wrap gap-1">
            {post.hashtags.slice(0, 8).map(tag => (
              <span key={tag} className="text-xs bg-white border border-slate-200 text-slate-600 px-2 py-0.5 rounded-full">{tag}</span>
            ))}
            {post.hashtags.length > 8 && <span className="text-xs text-slate-400">+{post.hashtags.length - 8} more</span>}
          </div>
        </div>
      )}

      {post.engagement_tips?.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Tips</p>
          <ul className="space-y-0.5">
            {post.engagement_tips.map((tip, i) => (
              <li key={i} className="text-xs text-slate-600 flex items-start gap-1">
                <span className="text-emerald-500 mt-0.5">✓</span> {tip}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ContentCard({ item, onGenerate }: { item: ContentItem; onGenerate: (id: string, platform: string) => Promise<{ generated: Record<string, GeneratedPost> }> }) {
  const [expanded, setExpanded] = useState(false);
  const [generatingFor, setGeneratingFor] = useState<string | null>(null);
  const [generatedData, setGeneratedData] = useState<Record<string, GeneratedPost>>({});
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
  const cat = CATEGORY_LABELS[item.category] || CATEGORY_LABELS.other;

  const handleGenerate = async (platform: string) => {
    setGeneratingFor(platform);
    setExpanded(true);
    setSelectedPlatform(platform);
    const result = await onGenerate(item.id, platform);
    setGeneratedData(prev => ({ ...prev, ...result.generated }));
    setGeneratingFor(null);
  };

  return (
    <div className="card overflow-hidden">
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              {item.is_trending && (
                <span className="inline-flex items-center gap-1 text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
                  <TrendingUp size={10} /> Trending
                </span>
              )}
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cat.color}`}>{cat.label}</span>
              <span className="text-xs text-slate-400">{item.source_label}</span>
              <span className="text-xs text-slate-400">{timeAgo(item.published_at || item.fetched_at)}</span>
            </div>
            <h3 className="text-sm font-semibold text-slate-800 leading-snug line-clamp-2">{item.title}</h3>
          </div>
          <div className="shrink-0 flex flex-col items-end gap-1">
            <ScoreBar score={item.relevance_score} />
            {item.source_url && (
              <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-brand-600 transition">
                <ExternalLink size={13} />
              </a>
            )}
          </div>
        </div>

        {item.summary && <p className="mt-2 text-sm text-slate-600 leading-relaxed line-clamp-3">{item.summary}</p>}

        {item.key_points?.length > 0 && (
          <ul className="mt-2 space-y-0.5">
            {item.key_points.slice(0, 2).map((pt, i) => (
              <li key={i} className="text-xs text-slate-500 flex items-start gap-1">
                <span className="text-brand-400 mt-0.5">•</span> {pt}
              </li>
            ))}
          </ul>
        )}

        <div className="mt-3 flex flex-wrap gap-2 items-center">
          <span className="text-xs text-slate-500 font-medium">Generate for:</span>
          {PLATFORM_CONFIG.map(p => (
            <button
              key={p.key}
              onClick={() => handleGenerate(p.key)}
              disabled={generatingFor === p.key}
              className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border font-medium transition
                ${selectedPlatform === p.key && generatedData[p.key]
                  ? `${p.bg} ${p.color}`
                  : "bg-white border-slate-200 text-slate-600 hover:border-brand-300 hover:text-brand-600"
                } disabled:opacity-50 disabled:cursor-wait`}
            >
              <p.icon size={12} />
              {generatingFor === p.key ? "..." : p.label}
            </button>
          ))}
          <button
            onClick={() => handleGenerate("all")}
            disabled={generatingFor === "all"}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-gradient-to-r from-brand-500 to-purple-500 text-white font-medium hover:opacity-90 transition disabled:opacity-50"
          >
            <Sparkles size={12} />
            {generatingFor === "all" ? "Generating..." : "All platforms"}
          </button>
          {Object.keys(generatedData).length > 0 && (
            <button onClick={() => setExpanded(!expanded)} className="ml-auto flex items-center gap-1 text-xs text-brand-600 hover:underline">
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? "Hide" : "Show"} content
            </button>
          )}
        </div>
      </div>

      {expanded && Object.keys(generatedData).length > 0 && (
        <div className="border-t border-slate-100 p-4 bg-slate-50 space-y-3">
          {PLATFORM_CONFIG.filter(p => generatedData[p.key]).map(p => (
            <GeneratedPanel key={p.key} post={generatedData[p.key]} platform={p.key} />
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

  const { data: statsData } = useQuery({
    queryKey: ["agent-stats"],
    queryFn: () => getAgentStats().then(r => r.data),
    refetchInterval: 60_000,
  });

  const { data: feedData, isLoading } = useQuery({
    queryKey: ["agent-feed", selectedCategory, hoursBack],
    queryFn: () => getAgentFeed({ category: selectedCategory || undefined, hours_back: hoursBack, min_score: 0.3, limit: 30 }).then(r => r.data),
  });

  const triggerMut = useMutation({
    mutationFn: () => triggerCollection().then(r => r.data),
    onSuccess: () => {
      toast.success("Collection started! Check back in ~1 minute.");
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["agent-feed"] }), 30_000);
    },
    onError: () => toast.error("Failed to trigger collection"),
  });

  const generateMut = useMutation({
    mutationFn: ({ id, platform }: { id: string; platform: string }) => generateContent(id, platform).then(r => r.data),
    onSuccess: (data) => {
      toast.success(`Generated for ${data.platforms_generated.length} platform(s)!`);
    },
    onError: () => toast.error("Generation failed. Check your API keys in .env"),
  });

  const handleGenerate = useCallback(async (id: string, platform: string) => {
    const data = await generateMut.mutateAsync({ id, platform });
    return { generated: data.generated };
  }, [generateMut]);

  const categories = feedData?.categories || [];

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="bg-white border-b border-slate-100 px-6 py-5">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                <div className="w-8 h-8 gradient-bg rounded-xl flex items-center justify-center">
                  <Sparkles size={16} className="text-white" />
                </div>
                Content Intelligence
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">AI-curated tech news → ready-to-post content. Free sources only.</p>
            </div>
            <button
              onClick={() => triggerMut.mutate()}
              disabled={triggerMut.isPending}
              className="flex items-center gap-2 btn-primary px-4 py-2 rounded-xl text-sm font-semibold disabled:opacity-60"
            >
              <RefreshCw size={14} className={triggerMut.isPending ? "animate-spin" : ""} />
              {triggerMut.isPending ? "Running..." : "Collect now"}
            </button>
          </div>

          {statsData && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
              <StatCard icon={Newspaper}  label="Collected (24h)"      value={statsData.items_collected_24h}  color="bg-brand-500" />
              <StatCard icon={Star}       label="Top stories"           value={statsData.top_stories_24h}      color="bg-purple-500" />
              <StatCard icon={TrendingUp} label="Trending now"          value={statsData.trending_now}          color="bg-amber-500" />
              <StatCard icon={Zap}        label="Content created (7d)"  value={statsData.content_generated_7d} color="bg-emerald-500" />
            </div>
          )}
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-6 space-y-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 text-sm text-slate-500">
            <Filter size={14} />
            <span className="font-medium">Filter:</span>
          </div>
          <button
            onClick={() => setSelectedCategory(null)}
            className={`text-xs px-3 py-1.5 rounded-full border font-medium transition ${!selectedCategory ? "bg-brand-600 text-white border-brand-600" : "bg-white border-slate-200 text-slate-600 hover:border-brand-300"}`}
          >
            All
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
              className={`text-xs px-3 py-1.5 rounded-full border font-medium transition ${selectedCategory === cat ? "bg-brand-600 text-white border-brand-600" : "bg-white border-slate-200 text-slate-600 hover:border-brand-300"}`}
            >
              {CATEGORY_LABELS[cat]?.label || cat}
            </button>
          ))}
          <div className="ml-auto flex items-center gap-2 text-sm text-slate-500">
            <Clock size={13} />
            <select value={hoursBack} onChange={e => setHoursBack(Number(e.target.value))} className="border border-slate-200 rounded-lg px-2 py-1 text-xs text-slate-700 bg-white">
              <option value={24}>Last 24h</option>
              <option value={48}>Last 48h</option>
              <option value={72}>Last 3 days</option>
              <option value={168}>Last 7 days</option>
            </select>
          </div>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[1,2,3].map(i => (
              <div key={i} className="card p-4 animate-pulse">
                <div className="h-4 bg-slate-100 rounded w-3/4 mb-2" />
                <div className="h-3 bg-slate-100 rounded w-full mb-1" />
                <div className="h-3 bg-slate-100 rounded w-2/3" />
              </div>
            ))}
          </div>
        ) : feedData?.items.length === 0 ? (
          <div className="card p-12 text-center">
            <Newspaper size={32} className="text-slate-300 mx-auto mb-3" />
            <h3 className="text-slate-600 font-medium mb-1">No stories yet</h3>
            <p className="text-sm text-slate-400 mb-4">Click "Collect now" to fetch the latest tech news from all sources.</p>
            <button onClick={() => triggerMut.mutate()} className="btn-primary px-4 py-2 rounded-xl text-sm font-semibold">
              Start collecting
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {feedData?.items.map(item => (
              <ContentCard key={item.id} item={item} onGenerate={handleGenerate} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
