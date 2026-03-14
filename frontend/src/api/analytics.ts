import api from "./client";
import type { AnalyticsSummary } from "../types";
export const getAnalytics = () => api.get<AnalyticsSummary>("/analytics/summary");