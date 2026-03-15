import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import Layout from "./components/ui/Layout";
import ProtectedRoute from "./components/ui/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import OAuthCallbackPage from "./pages/OAuthCallbackPage";
import DashboardPage from "./pages/DashboardPage";
import UploadPage from "./pages/UploadPage";
import HistoryPage from "./pages/HistoryPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import SettingsPage from "./pages/SettingsPage";
import AgentPage from "./pages/AgentPage";

// ── DEV BYPASS ────────────────────────────────────────────────────────────
const DEV_BYPASS_AUTH = true;

const DEV_USER = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "dev@local.dev",
  name: "Dev User",
  avatar_url: null,
  google_id: null,
  is_active: true,
  connected_platforms: [],
  encrypted_platform_tokens: {},
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};
// ─────────────────────────────────────────────────────────────────────────

export default function App() {
  const { setUser, setAccessToken, setLoading } = useAuthStore();

  useEffect(() => {
    if (DEV_BYPASS_AUTH) {
      setUser(DEV_USER as any);
      setAccessToken("dev-bypass-token");
      setLoading(false);
      return;
    }

    const restoreSession = async () => {
      try {
        const meResp = await fetch("/api/v1/auth/me", {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });

        if (meResp.ok) {
          const data = await meResp.json();
          setUser(data.user ?? data);
          if (data.access_token) setAccessToken(data.access_token);
          return;
        }

        if (meResp.status !== 401) {
          console.warn("[App] /auth/me returned", meResp.status);
          return;
        }

        const refreshResp = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });

        if (!refreshResp.ok) return;

        const refreshData = await refreshResp.json();
        const newToken = refreshData.access_token ?? null;
        if (newToken) setAccessToken(newToken);

        const me2Resp = await fetch("/api/v1/auth/me", {
          method: "GET",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            ...(newToken ? { Authorization: `Bearer ${newToken}` } : {}),
          },
        });

        if (me2Resp.ok) {
          const data2 = await me2Resp.json();
          setUser(data2.user ?? data2);
          if (data2.access_token) setAccessToken(data2.access_token);
        }
      } catch (err) {
        console.warn("[App] Session restore error:", err);
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Routes>
      <Route path="/login"    element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/auth/google/callback" element={<OAuthCallbackPage />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/agent" element={<AgentPage />} />
        <Route path="/upload"    element={<UploadPage />} />
        <Route path="/history"   element={<HistoryPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings"  element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}