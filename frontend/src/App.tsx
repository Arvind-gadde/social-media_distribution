import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import api from "./api/client";
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

export default function App() {
  const setUser = useAuthStore((s) => s.setUser);
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setLoading = useAuthStore((s) => s.setLoading);

  useEffect(() => {
    // Safety net: no matter what happens, loading MUST stop within 8 seconds.
    // This prevents a stuck spinner if the interceptor swallows a rejection.
    const safetyTimer = setTimeout(() => {
      if (useAuthStore.getState().isLoading) {
        console.warn("[App] Safety timeout fired — forcing isLoading=false");
        useAuthStore.getState().setLoading(false);
      }
    }, 8000);

    const restoreSession = async () => {
      try {
        // Step 1: try /auth/me via access cookie
        // Use a raw fetch here to BYPASS the Axios interceptor entirely.
        // This prevents the interceptor from intercepting the 401, trying its own
        // refresh, calling logout(), and corrupting the promise chain before
        // our catch block even runs.
        const rawMe = await fetch("/api/v1/auth/me", {
          method: "GET",
          credentials: "include",          // sends cookies
          headers: { "Content-Type": "application/json" },
        });

        if (rawMe.ok) {
          const data = await rawMe.json();
          setUser(data.user ?? data);      // handle both {user, access_token} and plain user object
          if (data.access_token) setAccessToken(data.access_token);
          return;                          // ✅ done
        }

        if (rawMe.status !== 401) {
          // Server error (5xx) — don't try refresh, just stop loading
          console.error("[App] /auth/me returned", rawMe.status);
          return;
        }

        // Step 2: access cookie expired — try silent refresh via raw fetch
        const rawRefresh = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });

        if (!rawRefresh.ok) {
          // Refresh token also invalid — user genuinely not logged in
          // Do NOT call setUser(null) here — if a login just completed in another
          // tab or the interceptor already cleared it, we don't want to fight.
          return;
        }

        const refreshData = await rawRefresh.json();
        const newToken = refreshData.access_token ?? null;
        if (newToken) setAccessToken(newToken);

        // Step 3: retry /auth/me with the fresh token
        const rawMe2 = await fetch("/api/v1/auth/me", {
          method: "GET",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            ...(newToken ? { Authorization: `Bearer ${newToken}` } : {}),
          },
        });

        if (rawMe2.ok) {
          const data2 = await rawMe2.json();
          setUser(data2.user ?? data2);
          if (data2.access_token) setAccessToken(data2.access_token);
        }
      } catch (err) {
        // Network error or JSON parse failure — log and continue
        console.error("[App] Session restore failed:", err);
      } finally {
        // Always stop the spinner — no `cancelled` guard here so this
        // fires even if a stale effect cleanup ran.
        clearTimeout(safetyTimer);
        setLoading(false);
      }
    };

    restoreSession();

    // We do NOT set cancelled=true in cleanup here, intentionally.
    // The raw fetch calls are fire-and-forget and the finally always
    // calls setLoading(false), which is idempotent and safe to call twice.
    return () => clearTimeout(safetyTimer);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/auth/google/callback" element={<OAuthCallbackPage />} />

      {/* Protected routes */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}