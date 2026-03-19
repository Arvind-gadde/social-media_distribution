import api from "./client";

// ── Shared enriched item type ─────────────────────────────────────────────

export interface InsightDetail {
  id: string;
  content_item_id: string;
  virality_score: number;
  cross_source_count: number;
  trend_velocity: number;
  sentiment_breakdown: Record<string, number>;
  is_value_gap: boolean;
  gap_explanation: string | null;
  suggested_angle: string | null;
  broll_assets: BrollAsset[];
  fact_check_passed: boolean | null;
  fact_check_confidence: number | null;
  flagged_claims: FlaggedClaim[];
  computed_at: string;
}

export interface BrollAsset {
  type: string;  // "github" | "youtube" | "arxiv" | "image" | …
  url: string;
  label: string;
}

export interface FlaggedClaim {
  claim: string;
  verdict: "verified" | "plausible" | "unverified" | "disputed";
  note: string | null;
}

export interface EnrichedItem {
  id: string;
  title: string;
  source_label: string;
  source_url: string | null;
  category: string;
  relevance_score: number;
  is_trending: boolean;
  summary: string | null;
  key_points: string[];
  author: string | null;
  published_at: string | null;
  fetched_at: string;
  // Flattened convenience fields (always present)
  virality_score: number;
  is_value_gap: boolean;
  suggested_angle: string | null;
  fact_check_passed: boolean | null;
  broll_assets: BrollAsset[];
  // Full nested insight (present when the item has been analysed)
  insight: InsightDetail | null;
}

// ── Pipeline run types ────────────────────────────────────────────────────

export interface StageTiming {
  scout_s: number | null;
  analyst_s: number | null;
  checker_s: number | null;
  creative_s: number | null;
}

export interface RunCounts {
  fetched: number;
  new: number;
  scored: number;
  fact_checked: number;
  generated: number;
  gap_signals: number;
}

export interface PipelineRun {
  id: string;
  triggered_by: string;
  status: "running" | "success" | "partial" | "failed" | "unknown";
  stage_timings: StageTiming;
  counts: RunCounts;
  stage_errors: Array<{ stage: string; error: string }>;
  started_at: string;
  finished_at: string | null;
  total_duration_s: number | null;
}

// ── Insights stats ────────────────────────────────────────────────────────

export interface InsightStats {
  analysed_items_24h: number;
  value_gap_picks_24h: number;
  fact_check_flags_24h: number;
  auto_generated_posts_7d: number;
  avg_virality_24h: number;
  last_pipeline_run: PipelineRun | null;
}

// ── API calls ─────────────────────────────────────────────────────────────

export const getInsightFeed = (params?: {
  hours_back?: number;
  min_virality?: number;
  value_gap_only?: boolean;
  fact_check_failed?: boolean;
  limit?: number;
  offset?: number;
}) =>
  api.get<{
    items: EnrichedItem[];
    total: number;
    filters: { hours_back: number; min_virality: number; value_gap_only: boolean };
  }>("/insights/feed", { params });

export const getGapPicks = (params?: { hours_back?: number; limit?: number }) =>
  api.get<{ gap_picks: EnrichedItem[]; count: number }>("/insights/gap-picks", { params });

export const getItemInsight = (itemId: string) =>
  api.get<EnrichedItem & { generated_posts: Record<string, unknown> }>(
    `/insights/item/${itemId}`
  );

export const getPipelineRuns = (params?: { limit?: number; offset?: number }) =>
  api.get<{
    runs: PipelineRun[];
    total: number;
    last_run_status: string | null;
    last_success_at: string | null;
  }>("/insights/runs", { params });

export const getInsightStats = () => api.get<InsightStats>("/insights/stats");