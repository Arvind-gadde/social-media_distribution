import { useState, type ElementType } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Flame, TrendingUp, ShieldCheck, ShieldAlert, ShieldQuestion,
  Zap, Activity, CheckCircle2, XCircle, AlertTriangle, Clock,
  RefreshCw, ExternalLink, ChevronRight, BarChart3, Layers, Filter,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  getGapPicks, getInsightFeed, getPipelineRuns, getInsightStats,
  type EnrichedItem, type PipelineRun, type FlaggedClaim, type BrollAsset,
} from "../api/insights";
import { generateContent } from "../api/agent";
import { hasApiResponse } from "../lib/apiErrors";

// ─── helpers ─────────────────────────────────────────────────────────────────

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

function fmtSeconds(s: number | null): string {
  if (s == null) return "—";
  if (s < 60) return `${s.toFixed(1)}s`;
  return `${Math.round(s / 60)}m ${Math.round(s % 60)}s`;
}

// ─── Virality ring ────────────────────────────────────────────────────────────

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

// ─── Fact-check badge ─────────────────────────────────────────────────────────

function FactBadge({ passed }: { passed: boolean | null }) {
  if (passed === null)
    return <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-white/[0.07] text-white/40 border border-white/[0.09]"><ShieldQuestion size={9} /> Unverified</span>;
  if (passed)
    return <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/25"><ShieldCheck size={9} /> Verified</span>;
  return <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/25"><ShieldAlert size={9} /> Flagged</span>;
}

// ─── Sentiment bar ────────────────────────────────────────────────────────────

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

// ─── B-Roll chips ─────────────────────────────────────────────────────────────

const BROLL_ICONS: Record<string, string> = {
  github: "🐙", youtube: "▶️", arxiv: "📄", image: "🖼️", demo: "🎬", tweet: "𝕏",
};

function BrollChips({ assets }: { assets: BrollAsset[] }) {
  if (!assets.length) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1.5">
      {assets.slice(0, 4).map((a, i) => (
        <a key={i} href={a.url} target="_blank" rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] hover:bg-white/[0.12] text-white/50 border border-white/[0.08] transition-colors">
          <span>{BROLL_ICONS[a.type] ?? "🔗"}</span>
          {a.label.slice(0, 20)}
        </a>
      ))}
      {assets.length > 4 && <span className="text-[10px] text-white/25 self-center">+{assets.length - 4}</span>}
    </div>
  );
}

// ─── Verdict styles ───────────────────────────────────────────────────────────

const VERDICT_STYLE: Record<FlaggedClaim["verdict"], string> = {
  verified:   "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  plausible:  "text-sky-400 bg-sky-500/10 border-sky-500/30",
  unverified: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  disputed:   "text-red-400 bg-red-500/10 border-red-500/30",
};

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, sub, accent }: {
  icon: ElementType; label: string; value: string | number; sub?: string; accent: string;
}) {
  return (
    <div className="glass rounded-2xl p-4 flex items-start gap-3">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${accent}`}>
        <Icon size={15} className="text-white" />
      </div>
      <div className="min-w-0">
        <p className="text-xl font-bold text-white leading-none">{value}</p>
        <p className="text-xs text-white/45 mt-0.5">{label}</p>
        {sub && <p className="text-[10px] text-white/25 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ─── Gap pick card ────────────────────────────────────────────────────────────

function GapPickCard({ item, onGenerate }: { item: EnrichedItem; onGenerate: (id: string) => void }) {
  return (
    <div className="glass-card p-5 hover:border-amber-500/25 transition-all duration-200 space-y-3">
      <div className="flex items-start gap-3">
        <ViralityRing score={item.virality_score} />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-400/25 font-semibold">
              <Flame size={9} /> Value Gap
            </span>
            <FactBadge passed={item.fact_check_passed} />
            <span className="text-[10px] text-white/35">{item.source_label}</span>
            <span className="text-[10px] text-white/20">·</span>
            <span className="text-[10px] text-white/35">{timeAgo(item.published_at || item.fetched_at)}</span>
          </div>
          {item.source_url ? (
            <a href={item.source_url} target="_blank" rel="noopener noreferrer"
              className="text-sm font-semibold text-white hover:text-white/90 leading-snug group flex items-start gap-1 transition-colors">
              {item.title}
              <ExternalLink size={10} className="shrink-0 mt-0.5 text-white/20 group-hover:text-white/50" />
            </a>
          ) : (
            <p className="text-sm font-semibold text-white leading-snug">{item.title}</p>
          )}
        </div>
      </div>

      {item.insight?.gap_explanation && (
        <p className="text-xs text-white/55 leading-relaxed border-l-2 border-amber-500/30 pl-3">
          {item.insight.gap_explanation}
        </p>
      )}

      {item.suggested_angle && (
        <div className="bg-white/[0.04] border border-white/[0.07] rounded-xl p-3">
          <p className="text-[10px] text-white/35 uppercase tracking-wider mb-1 flex items-center gap-1">
            <Zap size={9} /> Suggested angle
          </p>
          <p className="text-xs text-white/75 leading-relaxed">{item.suggested_angle}</p>
        </div>
      )}

      <BrollChips assets={item.broll_assets} />

      <div className="flex flex-col gap-3 pt-1 sm:flex-row sm:items-end sm:justify-between">
        {item.insight && <SentimentBar breakdown={item.insight.sentiment_breakdown} />}
        <button onClick={() => onGenerate(item.id)}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-white transition-all hover:brightness-110 sm:ml-auto sm:w-auto"
          style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}>
          <Zap size={11} /> Generate content <ChevronRight size={11} />
        </button>
      </div>
    </div>
  );
}

// ─── Intel feed row ───────────────────────────────────────────────────────────

function IntelFeedRow({ item }: { item: EnrichedItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="glass-card overflow-hidden hover:border-white/[0.15] transition-all p-0">
      <button className="w-full text-left p-4" onClick={() => setExpanded((v) => !v)}>
        <div className="flex items-start gap-3">
          <ViralityRing score={item.virality_score} />
          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex flex-wrap items-center gap-1.5">
              {item.is_value_gap && (
                <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-400/20 font-semibold">
                  <Flame size={9} /> Gap
                </span>
              )}
              <FactBadge passed={item.fact_check_passed} />
              {item.is_trending && (
                <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/25">
                  <TrendingUp size={9} /> Trending
                </span>
              )}
              <span className="text-[10px] text-white/35">{item.source_label}</span>
              <span className="w-full text-[10px] text-white/25 sm:ml-auto sm:w-auto">{timeAgo(item.published_at || item.fetched_at)}</span>
            </div>
            <p className="text-sm font-semibold text-white leading-snug line-clamp-2">{item.title}</p>
            {item.summary && !expanded && (
              <p className="text-xs text-white/40 leading-relaxed line-clamp-1">{item.summary}</p>
            )}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-white/[0.07] p-4 bg-white/[0.02] space-y-3 animate-fade-in">
          {item.summary && <p className="text-xs text-white/55 leading-relaxed">{item.summary}</p>}
          {item.suggested_angle && (
            <div className="bg-white/[0.04] border border-white/[0.07] rounded-lg p-3">
              <p className="text-[10px] text-white/35 uppercase tracking-wider mb-1 flex items-center gap-1"><Zap size={9} /> Angle</p>
              <p className="text-xs text-white/70">{item.suggested_angle}</p>
            </div>
          )}
          {item.insight?.flagged_claims && item.insight.flagged_claims.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] text-white/35 uppercase tracking-wider">Fact-check claims</p>
              {item.insight.flagged_claims.map((fc, i) => (
                <div key={i} className={`rounded-lg border px-3 py-2 text-[11px] ${VERDICT_STYLE[fc.verdict]}`}>
                  <span className="font-semibold capitalize">{fc.verdict}</span>
                  {" — "}{fc.claim}
                  {fc.note && <span className="block mt-0.5 opacity-70">{fc.note}</span>}
                </div>
              ))}
            </div>
          )}
          <BrollChips assets={item.broll_assets} />
          {item.source_url && (
            <a href={item.source_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-brand-300 hover:text-brand-200 transition-colors">
              View source <ExternalLink size={11} />
            </a>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Pipeline run row ─────────────────────────────────────────────────────────

const STATUS_STYLE: Record<string, { color: string; icon: ElementType; label: string }> = {
  success: { color: "text-emerald-400", icon: CheckCircle2, label: "Success" },
  partial: { color: "text-amber-400",   icon: AlertTriangle, label: "Partial" },
  failed:  { color: "text-red-400",     icon: XCircle,       label: "Failed"  },
  running: { color: "text-blue-400",    icon: RefreshCw,     label: "Running" },
  unknown: { color: "text-white/30",    icon: Clock,         label: "Unknown" },
};

function PipelineRunRow({ run }: { run: PipelineRun }) {
  const [expanded, setExpanded] = useState(false);
  const s = STATUS_STYLE[run.status] ?? STATUS_STYLE.unknown;
  const StatusIcon = s.icon;
  const stages = [
    { key: "scout_s",    label: "Scout"    },
    { key: "analyst_s",  label: "Analyst"  },
    { key: "checker_s",  label: "Checker"  },
    { key: "creative_s", label: "Creative" },
  ] as const;

  const maxDuration = Math.max(...stages.map((st) => (run.stage_timings[st.key] ?? 0)));

  return (
    <div className="glass-card overflow-hidden p-0">
      <button className="flex w-full flex-col gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.03] sm:flex-row sm:items-center" onClick={() => setExpanded((v) => !v)}>
        <StatusIcon size={15} className={`shrink-0 ${s.color}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-semibold ${s.color}`}>{s.label}</span>
            <span className="text-xs text-white/35">{timeAgo(run.started_at)}</span>
            <span className="text-[10px] text-white/25 capitalize">via {run.triggered_by.replace("_", " ")}</span>
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-3 text-[10px] text-white/35">
            <span>{run.counts.fetched} fetched</span>
            <span>{run.counts.new} new</span>
            <span>{run.counts.gap_signals} gaps</span>
            {run.total_duration_s != null && (
              <span className="sm:ml-auto">{fmtSeconds(run.total_duration_s)} total</span>
            )}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-white/[0.07] p-4 bg-white/[0.02] space-y-3 animate-fade-in">
          <div className="space-y-2">
            {stages.map(({ key, label }) => {
              const val = run.stage_timings[key];
              const pct = maxDuration > 0 && val != null ? (val / maxDuration) * 100 : 0;
              return (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-[11px] text-white/40 w-16 shrink-0">{label}</span>
                  <div className="flex-1 h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-brand-500 transition-all" style={{ width: val != null ? `${pct}%` : "0%" }} />
                  </div>
                  <span className="text-[11px] text-white/45 w-10 text-right shrink-0">{fmtSeconds(val)}</span>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-3">
            {[
              ["Fetched", run.counts.fetched], ["New", run.counts.new], ["Scored", run.counts.scored],
              ["Fact-checked", run.counts.fact_checked], ["Generated", run.counts.generated], ["Gap signals", run.counts.gap_signals],
            ].map(([label, val]) => (
              <div key={label as string} className="bg-white/[0.04] rounded-lg p-2 text-center border border-white/[0.06]">
                <p className="text-white/80 font-semibold">{val as number}</p>
                <p className="text-white/35 mt-0.5">{label as string}</p>
              </div>
            ))}
          </div>

          {run.stage_errors.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] text-white/35 uppercase tracking-wider">Stage errors</p>
              {run.stage_errors.map((e, i) => (
                <div key={i} className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-[11px]">
                  <span className="text-red-300 font-semibold capitalize">{e.stage}</span>
                  <span className="text-white/50"> — {e.error}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────

type Tab = "gap-picks" | "feed" | "pipeline";

const TABS: { id: Tab; label: string; icon: ElementType }[] = [
  { id: "gap-picks", label: "Gap Picks",          icon: Flame    },
  { id: "feed",      label: "Intelligence Feed",   icon: Layers   },
  { id: "pipeline",  label: "Pipeline Health",     icon: Activity },
];

// ─── Main page ────────────────────────────────────────────────────────────────

export default function InsightsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("gap-picks");
  const [hoursBack, setHoursBack] = useState(48);
  const [minVirality, setMinVirality] = useState(0);
  const [valueGapOnly, setValueGapOnly] = useState(false);
  const [feedPage, setFeedPage] = useState(0);
  const FEED_PAGE_SIZE = 20;

  const { data: stats } = useQuery({
    queryKey: ["insight-stats"],
    queryFn: () => getInsightStats().then((r) => r.data),
    refetchInterval: 30_000,
  });

  const { data: gapData, isLoading: gapLoading } = useQuery({
    queryKey: ["gap-picks", hoursBack],
    queryFn: () => getGapPicks({ hours_back: hoursBack, limit: 10 }).then((r) => r.data),
    enabled: activeTab === "gap-picks",
  });

  const { data: feedData, isLoading: feedLoading } = useQuery({
    queryKey: ["insight-feed", hoursBack, minVirality, valueGapOnly, feedPage],
    queryFn: () => getInsightFeed({ hours_back: hoursBack, min_virality: minVirality, value_gap_only: valueGapOnly, limit: FEED_PAGE_SIZE, offset: feedPage * FEED_PAGE_SIZE }).then((r) => r.data),
    enabled: activeTab === "feed",
    placeholderData: (prev) => prev,
  });

  const { data: runsData, isLoading: runsLoading } = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: () => getPipelineRuns({ limit: 20 }).then((r) => r.data),
    enabled: activeTab === "pipeline",
    refetchInterval: 15_000,
  });

  const handleGenerate = async (itemId: string) => {
    try {
      await generateContent(itemId, "all");
      toast.success("Generation started! Switch to Agent tab to view.");
      navigate("/agent");
    } catch (error) {
      if (!hasApiResponse(error)) {
        toast.error("Generation failed. Check your connection.");
      }
    }
  };

  const feedItems = feedData?.items ?? [];
  const feedTotal = feedData?.total ?? 0;
  const feedTotalPages = Math.ceil(feedTotal / FEED_PAGE_SIZE);

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-1 pt-1 mb-5">
        <div className="flex flex-wrap items-start gap-3">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0" style={{ background: "linear-gradient(135deg,#f59e0b,#ef4444)" }}>
                <Flame size={15} className="text-white" />
              </div>
              Insights
            </h1>
            <p className="mt-1 text-sm text-white/45 sm:ml-10">Virality · Value gaps · Fact-check · Pipeline health</p>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 gap-2 mt-3 sm:grid-cols-4">
            <StatCard icon={BarChart3}   label="Analysed (24h)"      value={stats.analysed_items_24h}     accent="bg-brand-600/70" />
            <StatCard icon={Flame}       label="Gap picks (24h)"      value={stats.value_gap_picks_24h}    accent="bg-amber-600/70" />
            <StatCard icon={ShieldAlert} label="Fact flags (24h)"     value={stats.fact_check_flags_24h}   sub="Claims to review" accent="bg-red-600/70" />
            <StatCard icon={Zap}         label="Auto-generated (7d)"  value={stats.auto_generated_posts_7d} accent="bg-emerald-600/70" />
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="mb-5 flex overflow-x-auto border-b border-white/[0.08]">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-1.5 text-sm font-semibold px-4 py-2.5 rounded-t-lg border-b-2 transition-all ${
              activeTab === id
                ? "border-brand-500 text-white bg-white/[0.06]"
                : "border-transparent text-white/40 hover:text-white/70 hover:bg-white/[0.04]"
            }`}
          >
            <Icon size={13} />
            <span className="hidden sm:inline">{label}</span>
            <span className="sm:hidden">{label.split(" ")[0]}</span>
          </button>
        ))}
      </div>

      {/* Shared filter bar */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <Clock size={11} className="text-white/30" />
        {[{ label: "24h", value: 24 }, { label: "48h", value: 48 }, { label: "7d", value: 168 }].map((opt) => (
          <button key={opt.value}
            onClick={() => { setHoursBack(opt.value); setFeedPage(0); }}
            className={`text-xs px-3 py-1.5 rounded-full border font-semibold transition-all ${
              hoursBack === opt.value
                ? "bg-brand-600 border-brand-600 text-white"
                : "border-white/[0.09] text-white/45 bg-white/[0.04] hover:border-white/20 hover:text-white"
            }`}
          >
            {opt.label}
          </button>
        ))}

        {activeTab === "feed" && (
          <>
            <div className="h-4 border-l border-white/[0.09] mx-0.5" />
            <Filter size={11} className="text-white/30" />
            <button
              onClick={() => { setValueGapOnly((v) => !v); setFeedPage(0); }}
              className={`text-xs px-3 py-1.5 rounded-full border font-semibold transition-all flex items-center gap-1.5 ${
                valueGapOnly ? "bg-amber-600/20 border-amber-500/40 text-amber-300" : "border-white/[0.09] text-white/45 bg-white/[0.04] hover:border-white/20"
              }`}
            >
              <Flame size={10} /> Gap only
            </button>
            {[{ label: "All virality", value: 0 }, { label: "≥ 45%", value: 0.45 }, { label: "≥ 70%", value: 0.70 }].map((opt) => (
              <button key={opt.value}
                onClick={() => { setMinVirality(opt.value); setFeedPage(0); }}
                className={`text-xs px-3 py-1.5 rounded-full border font-semibold transition-all ${
                  minVirality === opt.value
                    ? "bg-brand-600 border-brand-600 text-white"
                    : "border-white/[0.09] text-white/45 bg-white/[0.04] hover:border-white/20 hover:text-white"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </>
        )}
      </div>

      {/* Gap Picks */}
      {activeTab === "gap-picks" && (
        gapLoading ? (
          <div className="space-y-3">
            {[1,2,3].map(i => (
              <div key={i} className="glass-card p-5 animate-pulse space-y-3">
                <div className="flex gap-3"><div className="skeleton w-11 h-11 rounded-full shrink-0" /><div className="flex-1 space-y-2"><div className="skeleton h-2.5 w-3/4" /><div className="skeleton h-2 w-1/2" /></div></div>
              </div>
            ))}
          </div>
        ) : gapData?.gap_picks.length === 0 ? (
          <div className="card py-20 text-center space-y-3">
            <Flame size={32} className="text-white/15 mx-auto" />
            <h3 className="text-sm font-semibold text-white/45">No gap picks yet</h3>
            <p className="text-xs text-white/30">Gap picks appear after the analyst pipeline runs and identifies underexplored angles.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {(gapData?.gap_picks ?? []).map((item) => (
              <GapPickCard key={item.id} item={item} onGenerate={handleGenerate} />
            ))}
          </div>
        )
      )}

      {/* Intelligence Feed */}
      {activeTab === "feed" && (
        <>
          {feedTotal > 0 && !feedLoading && (
            <p className="text-xs text-white/30 mb-3">{Math.min((feedPage + 1) * FEED_PAGE_SIZE, feedTotal)} of {feedTotal} items</p>
          )}
          {feedLoading && feedPage === 0 ? (
            <div className="space-y-2">
              {[1,2,3,4].map(i => (
                <div key={i} className="glass-card p-4 animate-pulse space-y-2">
                  <div className="flex gap-3"><div className="skeleton w-11 h-11 rounded-full shrink-0" /><div className="flex-1 space-y-2"><div className="skeleton h-2 w-2/3" /><div className="skeleton h-3 w-full" /></div></div>
                </div>
              ))}
            </div>
          ) : feedItems.length === 0 ? (
            <div className="card py-20 text-center space-y-3">
              <Layers size={32} className="text-white/15 mx-auto" />
              <h3 className="text-sm font-semibold text-white/45">No items match your filters</h3>
              <p className="text-xs text-white/30">Try a wider time range or lower virality threshold.</p>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                {feedItems.map((item) => <IntelFeedRow key={item.id} item={item} />)}
              </div>
              {feedTotalPages > 1 && (
                <div className="flex flex-col gap-2 pt-4 sm:flex-row sm:items-center sm:justify-between">
                  <button onClick={() => setFeedPage((p) => Math.max(0, p - 1))} disabled={feedPage === 0}
                    className="text-sm px-4 py-2 rounded-xl border border-white/[0.09] text-white/50 hover:bg-white/[0.07] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all">
                    ← Prev
                  </button>
                  <span className="text-sm text-white/35">Page {feedPage + 1} of {feedTotalPages}</span>
                  <button onClick={() => setFeedPage((p) => p + 1)} disabled={feedPage >= feedTotalPages - 1 || feedLoading}
                    className="flex items-center gap-2 text-sm px-4 py-2 rounded-xl text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                    style={{ background: "linear-gradient(135deg,#4f54e5,#7c3aed)" }}>
                    {feedLoading && <RefreshCw size={12} className="animate-spin" />}
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}

      {/* Pipeline Health */}
      {activeTab === "pipeline" && (
        <>
          {runsData?.last_run_status && (
            <div className={`mb-4 flex flex-col gap-3 rounded-xl border px-4 py-3 sm:flex-row sm:items-center ${
              runsData.last_run_status === "success" ? "bg-emerald-500/10 border-emerald-500/25"
              : runsData.last_run_status === "partial" ? "bg-amber-500/10 border-amber-500/25"
              : runsData.last_run_status === "failed" ? "bg-red-500/10 border-red-500/25"
              : "bg-white/[0.04] border-white/[0.09]"
            }`}>
              {runsData.last_run_status === "success" ? <CheckCircle2 size={15} className="text-emerald-400 shrink-0" />
               : runsData.last_run_status === "partial" ? <AlertTriangle size={15} className="text-amber-400 shrink-0" />
               : <XCircle size={15} className="text-red-400 shrink-0" />}
              <div>
                <p className="text-sm font-semibold text-white capitalize">Last run: {runsData.last_run_status}</p>
                {runsData.last_success_at && <p className="text-xs text-white/40">Last success {timeAgo(runsData.last_success_at)}</p>}
              </div>
              {stats && (
                <div className="w-full text-left sm:ml-auto sm:w-auto sm:text-right">
                  <p className="text-xs text-white/35">Avg virality (24h)</p>
                  <p className="text-sm font-bold text-white">{Math.round(stats.avg_virality_24h * 100)}%</p>
                </div>
              )}
            </div>
          )}

          {runsLoading ? (
            <div className="space-y-2">
              {[1,2,3].map(i => <div key={i} className="glass-card p-4 animate-pulse h-16" />)}
            </div>
          ) : !runsData?.runs.length ? (
            <div className="card py-20 text-center space-y-3">
              <Activity size={32} className="text-white/15 mx-auto" />
              <h3 className="text-sm font-semibold text-white/45">No pipeline runs yet</h3>
              <p className="text-xs text-white/30">Go to the Agent tab and hit "Collect now" to run the first pipeline.</p>
              <button onClick={() => navigate("/agent")}
                className="mt-2 text-sm px-5 py-2.5 rounded-xl font-semibold text-white"
                style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}>
                Go to Agent →
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {runsData.runs.map((run) => <PipelineRunRow key={run.id} run={run} />)}
            </div>
          )}
        </>
      )}
    </div>
  );
}
