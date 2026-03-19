import { useState, type ElementType } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Flame,
  TrendingUp,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  Zap,
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  BarChart3,
  Layers,
  Filter,
} from "lucide-react";
import toast from "react-hot-toast";
import {
  getGapPicks,
  getInsightFeed,
  getPipelineRuns,
  getInsightStats,
  type EnrichedItem,
  type PipelineRun,
  type FlaggedClaim,
  type BrollAsset,
} from "../api/insights";
import { generateContent } from "../api/agent";

// ─── helpers ────────────────────────────────────────────────────────────────

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

// ─── Virality ring ───────────────────────────────────────────────────────────

function ViralityRing({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const r = 16;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const color =
    pct >= 70
      ? "#10b981"  // emerald
      : pct >= 45
      ? "#f59e0b"  // amber
      : "#64748b"; // slate

  return (
    <div className="relative flex items-center justify-center w-11 h-11 shrink-0">
      <svg width="44" height="44" viewBox="0 0 44 44" className="-rotate-90">
        <circle cx="22" cy="22" r={r} stroke="#1e293b" strokeWidth="3" fill="none" />
        <circle
          cx="22"
          cy="22"
          r={r}
          stroke={color}
          strokeWidth="3"
          fill="none"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-[10px] font-bold text-slate-200">{pct}</span>
    </div>
  );
}

// ─── Fact-check badge ────────────────────────────────────────────────────────

function FactBadge({ passed }: { passed: boolean | null }) {
  if (passed === null) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-slate-700 text-slate-400 border border-slate-600">
        <ShieldQuestion size={9} /> Unverified
      </span>
    );
  }
  if (passed) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
        <ShieldCheck size={9} /> Verified
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 border border-red-500/30">
      <ShieldAlert size={9} /> Flagged
    </span>
  );
}

// ─── Sentiment bar ───────────────────────────────────────────────────────────

function SentimentBar({ breakdown }: { breakdown: Record<string, number> }) {
  const pos = Math.round((breakdown.positive ?? 0) * 100);
  const neg = Math.round((breakdown.negative ?? 0) * 100);
  const con = Math.round((breakdown.controversial ?? 0) * 100);
  if (pos + neg + con === 0) return null;

  return (
    <div className="space-y-0.5">
      <p className="text-[10px] text-slate-500 uppercase tracking-wider">Sentiment</p>
      <div className="flex h-1.5 rounded-full overflow-hidden w-24 gap-px">
        {pos > 0 && <div className="bg-emerald-500" style={{ width: `${pos}%` }} />}
        {neg > 0 && <div className="bg-red-500" style={{ width: `${neg}%` }} />}
        {con > 0 && <div className="bg-amber-500" style={{ width: `${con}%` }} />}
      </div>
    </div>
  );
}

// ─── B-Roll chips ────────────────────────────────────────────────────────────

const BROLL_ICONS: Record<string, string> = {
  github: "🐙",
  youtube: "▶️",
  arxiv: "📄",
  image: "🖼️",
  demo: "🎬",
  tweet: "𝕏",
};

function BrollChips({ assets }: { assets: BrollAsset[] }) {
  if (!assets.length) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1.5">
      {assets.slice(0, 4).map((a, i) => (
        <a
          key={i}
          href={a.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-slate-700 hover:bg-slate-600 text-slate-300 border border-slate-600 transition-colors"
        >
          <span>{BROLL_ICONS[a.type] ?? "🔗"}</span>
          {a.label.slice(0, 20)}
        </a>
      ))}
      {assets.length > 4 && (
        <span className="text-[10px] text-slate-600 self-center">+{assets.length - 4}</span>
      )}
    </div>
  );
}

// ─── Flagged claims ──────────────────────────────────────────────────────────

const VERDICT_STYLE: Record<FlaggedClaim["verdict"], string> = {
  verified:   "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  plausible:  "text-sky-400 bg-sky-500/10 border-sky-500/30",
  unverified: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  disputed:   "text-red-400 bg-red-500/10 border-red-500/30",
};

// ─── Stat card ───────────────────────────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: ElementType;
  label: string;
  value: string | number;
  sub?: string;
  accent: string;
}) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-4 flex items-start gap-3">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${accent}`}>
        <Icon size={16} className="text-white" />
      </div>
      <div className="min-w-0">
        <p className="text-xl font-bold text-white leading-none">{value}</p>
        <p className="text-xs text-slate-400 mt-0.5">{label}</p>
        {sub && <p className="text-[10px] text-slate-600 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ─── Gap pick card ───────────────────────────────────────────────────────────

function GapPickCard({
  item,
  onGenerate,
}: {
  item: EnrichedItem;
  onGenerate: (id: string) => void;
}) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-5 hover:border-amber-500/30 hover:bg-slate-800/80 transition-all duration-200 space-y-3">
      <div className="flex items-start gap-3">
        <ViralityRing score={item.virality_score} />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 font-medium">
              <Flame size={9} /> Value Gap
            </span>
            <FactBadge passed={item.fact_check_passed} />
            <span className="text-[10px] text-slate-500">{item.source_label}</span>
            <span className="text-[10px] text-slate-600">·</span>
            <span className="text-[10px] text-slate-500">
              {timeAgo(item.published_at || item.fetched_at)}
            </span>
          </div>

          {item.source_url ? (
            <a
              href={item.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-semibold text-slate-100 hover:text-white leading-snug group flex items-start gap-1 transition-colors"
            >
              {item.title}
              <ExternalLink size={10} className="shrink-0 mt-0.5 text-slate-600 group-hover:text-slate-400" />
            </a>
          ) : (
            <p className="text-sm font-semibold text-slate-100 leading-snug">{item.title}</p>
          )}
        </div>
      </div>

      {item.insight?.gap_explanation && (
        <p className="text-xs text-slate-400 leading-relaxed border-l-2 border-amber-500/30 pl-3">
          {item.insight.gap_explanation}
        </p>
      )}

      {item.suggested_angle && (
        <div className="bg-slate-900/60 border border-slate-700/40 rounded-xl p-3">
          <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
            <Zap size={9} /> Suggested angle
          </p>
          <p className="text-xs text-slate-200 leading-relaxed">{item.suggested_angle}</p>
        </div>
      )}

      <BrollChips assets={item.broll_assets} />

      <div className="flex items-center justify-between pt-1">
        {item.insight && (
          <SentimentBar breakdown={item.insight.sentiment_breakdown} />
        )}
        <button
          onClick={() => onGenerate(item.id)}
          className="ml-auto flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-semibold text-white transition-all"
          style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}
        >
          <Zap size={11} /> Generate content
          <ChevronRight size={11} />
        </button>
      </div>
    </div>
  );
}

// ─── Intel feed row ──────────────────────────────────────────────────────────

function IntelFeedRow({ item }: { item: EnrichedItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden hover:border-slate-600 transition-all">
      <button
        className="w-full text-left p-4"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-start gap-3">
          <ViralityRing score={item.virality_score} />
          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex flex-wrap items-center gap-1.5">
              {item.is_value_gap && (
                <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 font-medium">
                  <Flame size={9} /> Gap
                </span>
              )}
              <FactBadge passed={item.fact_check_passed} />
              {item.is_trending && (
                <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/30">
                  <TrendingUp size={9} /> Trending
                </span>
              )}
              <span className="text-[10px] text-slate-500">{item.source_label}</span>
              <span className="text-[10px] text-slate-500 ml-auto">
                {timeAgo(item.published_at || item.fetched_at)}
              </span>
            </div>
            <p className="text-sm font-semibold text-slate-100 leading-snug line-clamp-2">
              {item.title}
            </p>
            {item.summary && !expanded && (
              <p className="text-xs text-slate-500 leading-relaxed line-clamp-1">
                {item.summary}
              </p>
            )}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-700/50 p-4 bg-slate-900/40 space-y-3">
          {item.summary && (
            <p className="text-xs text-slate-400 leading-relaxed">{item.summary}</p>
          )}

          {item.suggested_angle && (
            <div className="bg-slate-800 border border-slate-700/40 rounded-lg p-3">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Zap size={9} /> Angle
              </p>
              <p className="text-xs text-slate-200">{item.suggested_angle}</p>
            </div>
          )}

          {item.insight?.flagged_claims && item.insight.flagged_claims.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider">
                Fact-check claims
              </p>
              {item.insight.flagged_claims.map((fc, i) => (
                <div
                  key={i}
                  className={`rounded-lg border px-3 py-2 text-[11px] ${VERDICT_STYLE[fc.verdict]}`}
                >
                  <span className="font-semibold capitalize">{fc.verdict}</span>
                  {" — "}
                  {fc.claim}
                  {fc.note && (
                    <span className="block mt-0.5 opacity-70">{fc.note}</span>
                  )}
                </div>
              ))}
            </div>
          )}

          <BrollChips assets={item.broll_assets} />

          {item.source_url && (
            <a
              href={item.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
            >
              View source <ExternalLink size={11} />
            </a>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Pipeline run row ────────────────────────────────────────────────────────

const STATUS_STYLE: Record<string, { color: string; icon: ElementType; label: string }> = {
  success: { color: "text-emerald-400", icon: CheckCircle2, label: "Success" },
  partial: { color: "text-amber-400",   icon: AlertTriangle, label: "Partial" },
  failed:  { color: "text-red-400",     icon: XCircle,       label: "Failed"  },
  running: { color: "text-blue-400",    icon: RefreshCw,     label: "Running" },
  unknown: { color: "text-slate-500",   icon: Clock,         label: "Unknown" },
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

  const maxDuration = Math.max(
    ...stages.map((st) => (run.stage_timings[st.key] ?? 0))
  );

  return (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden">
      <button
        className="w-full text-left px-4 py-3 flex items-center gap-3"
        onClick={() => setExpanded((v) => !v)}
      >
        <StatusIcon size={15} className={`shrink-0 ${s.color}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-semibold ${s.color}`}>{s.label}</span>
            <span className="text-xs text-slate-500">{timeAgo(run.started_at)}</span>
            <span className="text-[10px] text-slate-600 capitalize">
              via {run.triggered_by.replace("_", " ")}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-[10px] text-slate-500">
            <span>{run.counts.fetched} fetched</span>
            <span>{run.counts.new} new</span>
            <span>{run.counts.gap_signals} gaps</span>
            {run.total_duration_s != null && (
              <span className="ml-auto text-slate-600">
                {fmtSeconds(run.total_duration_s)} total
              </span>
            )}
          </div>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-700/40 p-4 bg-slate-900/40 space-y-3">
          {/* Stage timing bars */}
          <div className="space-y-2">
            {stages.map(({ key, label }) => {
              const val = run.stage_timings[key];
              const pct = maxDuration > 0 && val != null ? (val / maxDuration) * 100 : 0;
              return (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-[11px] text-slate-500 w-16 shrink-0">{label}</span>
                  <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-brand-500 transition-all"
                      style={{ width: val != null ? `${pct}%` : "0%" }}
                    />
                  </div>
                  <span className="text-[11px] text-slate-400 w-10 text-right shrink-0">
                    {fmtSeconds(val)}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Count summary */}
          <div className="grid grid-cols-3 gap-2 text-[11px]">
            {[
              ["Fetched",       run.counts.fetched],
              ["New",           run.counts.new],
              ["Scored",        run.counts.scored],
              ["Fact-checked",  run.counts.fact_checked],
              ["Generated",     run.counts.generated],
              ["Gap signals",   run.counts.gap_signals],
            ].map(([label, val]) => (
              <div key={label as string} className="bg-slate-800 rounded-lg p-2 text-center">
                <p className="text-slate-200 font-semibold">{val as number}</p>
                <p className="text-slate-500">{label as string}</p>
              </div>
            ))}
          </div>

          {/* Stage errors */}
          {run.stage_errors.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] text-slate-500 uppercase tracking-wider">Stage errors</p>
              {run.stage_errors.map((e, i) => (
                <div key={i} className="bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-[11px]">
                  <span className="text-red-400 font-semibold capitalize">{e.stage}</span>
                  <span className="text-slate-400"> — {e.error}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Tab definitions ─────────────────────────────────────────────────────────

type Tab = "gap-picks" | "feed" | "pipeline";

const TABS: { id: Tab; label: string; icon: ElementType }[] = [
  { id: "gap-picks", label: "Gap Picks",       icon: Flame      },
  { id: "feed",      label: "Intelligence Feed", icon: Layers     },
  { id: "pipeline",  label: "Pipeline Health",  icon: Activity   },
];

// ─── Main page ───────────────────────────────────────────────────────────────

export default function InsightsPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("gap-picks");
  const [hoursBack, setHoursBack] = useState(48);
  const [minVirality, setMinVirality] = useState(0);
  const [valueGapOnly, setValueGapOnly] = useState(false);
  const [feedPage, setFeedPage] = useState(0);
  const FEED_PAGE_SIZE = 20;

  // ── Stats ─────────────────────────────────────────────────────────────────
  const { data: stats } = useQuery({
    queryKey: ["insight-stats"],
    queryFn: () => getInsightStats().then((r) => r.data),
    refetchInterval: 30_000,
  });

  // ── Gap picks ─────────────────────────────────────────────────────────────
  const { data: gapData, isLoading: gapLoading } = useQuery({
    queryKey: ["gap-picks", hoursBack],
    queryFn: () => getGapPicks({ hours_back: hoursBack, limit: 10 }).then((r) => r.data),
    enabled: activeTab === "gap-picks",
  });

  // ── Intelligence feed ─────────────────────────────────────────────────────
  const { data: feedData, isLoading: feedLoading } = useQuery({
    queryKey: ["insight-feed", hoursBack, minVirality, valueGapOnly, feedPage],
    queryFn: () =>
      getInsightFeed({
        hours_back: hoursBack,
        min_virality: minVirality,
        value_gap_only: valueGapOnly,
        limit: FEED_PAGE_SIZE,
        offset: feedPage * FEED_PAGE_SIZE,
      }).then((r) => r.data),
    enabled: activeTab === "feed",
    placeholderData: (prev) => prev,
  });

  // ── Pipeline runs ─────────────────────────────────────────────────────────
  const { data: runsData, isLoading: runsLoading } = useQuery({
    queryKey: ["pipeline-runs"],
    queryFn: () => getPipelineRuns({ limit: 20 }).then((r) => r.data),
    enabled: activeTab === "pipeline",
    refetchInterval: 15_000,
  });

  // ── Handlers ─────────────────────────────────────────────────────────────
  const handleGenerate = async (itemId: string) => {
    try {
      await generateContent(itemId, "all");
      toast.success("Generation started! Switch to Agent tab to view.");
      navigate("/agent");
    } catch {
      toast.error("Generation failed.");
    }
  };

  const feedItems = feedData?.items ?? [];
  const feedTotal = feedData?.total ?? 0;
  const feedTotalPages = Math.ceil(feedTotal / FEED_PAGE_SIZE);

  return (
    <div className="min-h-screen bg-slate-900 animate-fade-in">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-10 border-b border-slate-800 bg-slate-900/90 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2.5">
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: "linear-gradient(135deg,#f59e0b,#ef4444)" }}
              >
                <Flame size={15} className="text-white" />
              </div>
              Insights Dashboard
            </h1>
            <p className="text-xs text-slate-500 mt-0.5 ml-10">
              Virality signals · Value gaps · Fact-check verdicts · Pipeline health
            </p>
          </div>
        </div>

        {/* Stats row */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            <StatCard
              icon={BarChart3}
              label="Analysed (24h)"
              value={stats.analysed_items_24h}
              accent="bg-brand-600"
            />
            <StatCard
              icon={Flame}
              label="Gap picks (24h)"
              value={stats.value_gap_picks_24h}
              accent="bg-amber-600"
            />
            <StatCard
              icon={ShieldAlert}
              label="Fact flags (24h)"
              value={stats.fact_check_flags_24h}
              sub="Claims to review"
              accent="bg-red-600"
            />
            <StatCard
              icon={Zap}
              label="Auto-generated (7d)"
              value={stats.auto_generated_posts_7d}
              accent="bg-emerald-600"
            />
          </div>
        )}
      </div>

      {/* ── Tabs ────────────────────────────────────────────────────────── */}
      <div className="px-6 pt-5">
        <div className="flex items-center gap-1 border-b border-slate-800 pb-0">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-t-lg border-b-2 transition-all ${
                activeTab === id
                  ? "border-brand-500 text-white bg-slate-800/50"
                  : "border-transparent text-slate-500 hover:text-slate-300 hover:bg-slate-800/30"
              }`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Tab content ─────────────────────────────────────────────────── */}
      <div className="p-6 space-y-4">

        {/* ── Shared filter bar ────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <Clock size={12} />
          </div>
          {[
            { label: "24h", value: 24 },
            { label: "48h", value: 48 },
            { label: "7d",  value: 168 },
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => { setHoursBack(opt.value); setFeedPage(0); }}
              className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-all ${
                hoursBack === opt.value
                  ? "bg-brand-600 border-brand-600 text-white"
                  : "border-slate-700 text-slate-400 bg-slate-800 hover:border-slate-500 hover:text-slate-300"
              }`}
            >
              {opt.label}
            </button>
          ))}

          {activeTab === "feed" && (
            <>
              <div className="h-4 border-l border-slate-700 mx-1" />
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <Filter size={11} />
              </div>
              <button
                onClick={() => { setValueGapOnly((v) => !v); setFeedPage(0); }}
                className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-all flex items-center gap-1.5 ${
                  valueGapOnly
                    ? "bg-amber-600/20 border-amber-500/40 text-amber-400"
                    : "border-slate-700 text-slate-400 bg-slate-800 hover:border-slate-500"
                }`}
              >
                <Flame size={10} /> Gap only
              </button>
              {[
                { label: "All virality", value: 0 },
                { label: "≥ 45%",        value: 0.45 },
                { label: "≥ 70%",        value: 0.70 },
              ].map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => { setMinVirality(opt.value); setFeedPage(0); }}
                  className={`text-xs px-3 py-1.5 rounded-full border font-medium transition-all ${
                    minVirality === opt.value
                      ? "bg-brand-600 border-brand-600 text-white"
                      : "border-slate-700 text-slate-400 bg-slate-800 hover:border-slate-500 hover:text-slate-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </>
          )}
        </div>

        {/* ══ Gap Picks tab ═══════════════════════════════════════════════ */}
        {activeTab === "gap-picks" && (
          <>
            {gapLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="bg-slate-800/50 border border-slate-700/60 rounded-2xl p-5 animate-pulse space-y-3"
                  >
                    <div className="flex gap-3">
                      <div className="w-11 h-11 rounded-full bg-slate-700 shrink-0" />
                      <div className="flex-1 space-y-2">
                        <div className="h-2.5 bg-slate-700 rounded w-3/4" />
                        <div className="h-2 bg-slate-700/50 rounded w-1/2" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : gapData?.gap_picks.length === 0 ? (
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-16 text-center">
                <Flame size={36} className="text-slate-700 mx-auto mb-3" />
                <h3 className="text-slate-400 font-semibold mb-1">No gap picks yet</h3>
                <p className="text-sm text-slate-600">
                  Gap picks appear after the analyst pipeline runs and identifies underexplored angles.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {(gapData?.gap_picks ?? []).map((item) => (
                  <GapPickCard key={item.id} item={item} onGenerate={handleGenerate} />
                ))}
              </div>
            )}
          </>
        )}

        {/* ══ Intelligence Feed tab ════════════════════════════════════════ */}
        {activeTab === "feed" && (
          <>
            {feedTotal > 0 && !feedLoading && (
              <p className="text-xs text-slate-600">
                {Math.min((feedPage + 1) * FEED_PAGE_SIZE, feedTotal)} of {feedTotal} items
              </p>
            )}

            {feedLoading && feedPage === 0 ? (
              <div className="space-y-2">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 animate-pulse space-y-2"
                  >
                    <div className="flex gap-3">
                      <div className="w-11 h-11 rounded-full bg-slate-700 shrink-0" />
                      <div className="flex-1 space-y-2">
                        <div className="h-2 bg-slate-700 rounded w-2/3" />
                        <div className="h-3 bg-slate-700 rounded w-full" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : feedItems.length === 0 ? (
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-16 text-center">
                <Layers size={36} className="text-slate-700 mx-auto mb-3" />
                <h3 className="text-slate-400 font-semibold mb-1">No items match your filters</h3>
                <p className="text-sm text-slate-600">Try a wider time range or lower virality threshold.</p>
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  {feedItems.map((item) => (
                    <IntelFeedRow key={item.id} item={item} />
                  ))}
                </div>

                {feedTotalPages > 1 && (
                  <div className="flex items-center justify-between pt-2">
                    <button
                      onClick={() => setFeedPage((p) => Math.max(0, p - 1))}
                      disabled={feedPage === 0}
                      className="text-sm px-4 py-2 rounded-xl border border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                    >
                      ← Prev
                    </button>
                    <span className="text-sm text-slate-500">
                      Page {feedPage + 1} of {feedTotalPages}
                    </span>
                    <button
                      onClick={() => setFeedPage((p) => p + 1)}
                      disabled={feedPage >= feedTotalPages - 1 || feedLoading}
                      className="flex items-center gap-2 text-sm px-4 py-2 rounded-xl text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                      style={{ background: "#4f54e5" }}
                    >
                      {feedLoading && <RefreshCw size={12} className="animate-spin" />}
                      Next →
                    </button>
                  </div>
                )}
              </>
            )}
          </>
        )}

        {/* ══ Pipeline Health tab ══════════════════════════════════════════ */}
        {activeTab === "pipeline" && (
          <>
            {/* Last run status banner */}
            {runsData?.last_run_status && (
              <div
                className={`flex items-center gap-3 rounded-xl border px-4 py-3 ${
                  runsData.last_run_status === "success"
                    ? "bg-emerald-500/10 border-emerald-500/30"
                    : runsData.last_run_status === "partial"
                    ? "bg-amber-500/10 border-amber-500/30"
                    : runsData.last_run_status === "failed"
                    ? "bg-red-500/10 border-red-500/30"
                    : "bg-slate-800 border-slate-700"
                }`}
              >
                {runsData.last_run_status === "success" ? (
                  <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                ) : runsData.last_run_status === "partial" ? (
                  <AlertTriangle size={16} className="text-amber-400 shrink-0" />
                ) : (
                  <XCircle size={16} className="text-red-400 shrink-0" />
                )}
                <div>
                  <p className="text-sm font-semibold text-slate-200 capitalize">
                    Last run: {runsData.last_run_status}
                  </p>
                  {runsData.last_success_at && (
                    <p className="text-xs text-slate-500">
                      Last success {timeAgo(runsData.last_success_at)}
                    </p>
                  )}
                </div>

                {/* Average virality from stats */}
                {stats && (
                  <div className="ml-auto text-right">
                    <p className="text-xs text-slate-500">Avg virality (24h)</p>
                    <p className="text-sm font-bold text-slate-200">
                      {Math.round(stats.avg_virality_24h * 100)}%
                    </p>
                  </div>
                )}
              </div>
            )}

            {runsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 animate-pulse"
                  >
                    <div className="flex gap-3 items-center">
                      <div className="w-4 h-4 rounded-full bg-slate-700 shrink-0" />
                      <div className="flex-1 space-y-2">
                        <div className="h-2.5 bg-slate-700 rounded w-24" />
                        <div className="h-2 bg-slate-700/50 rounded w-40" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : !runsData?.runs.length ? (
              <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-16 text-center">
                <Activity size={36} className="text-slate-700 mx-auto mb-3" />
                <h3 className="text-slate-400 font-semibold mb-1">No pipeline runs yet</h3>
                <p className="text-sm text-slate-600">
                  Go to the Agent tab and hit "Collect now" to run the first pipeline.
                </p>
                <button
                  onClick={() => navigate("/agent")}
                  className="mt-5 text-sm px-5 py-2.5 rounded-xl font-semibold text-white"
                  style={{ background: "linear-gradient(135deg,#6272f1,#a855f7)" }}
                >
                  Go to Agent →
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                {runsData.runs.map((run) => (
                  <PipelineRunRow key={run.id} run={run} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}