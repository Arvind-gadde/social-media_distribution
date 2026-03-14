import { useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "./store/authStore";
import { getMe } from "./api/auth";
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
  const setLoading = useAuthStore((s) => s.setLoading);

  // Restore session on page load by hitting /auth/me.
  // The HttpOnly cookie is sent automatically — no token in JS needed.
  useEffect(() => {
    // Only clear user if getMe fails AND store doesn't already have one.
    // This prevents a racing getMe() from overwriting a fresh login.
    getMe()
      .then((r) => setUser(r.data.user))
      .catch(() => {
        if (!useAuthStore.getState().user) setUser(null);
      })
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      {/* Google redirects here — must match GOOGLE_REDIRECT_URI in .env */}
      <Route path="/auth/google/callback" element={<OAuthCallbackPage />} />

      {/* Protected routes — wrapped in Layout (sidebar) */}
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

      {/* Fallback — redirect unknown paths to dashboard (ProtectedRoute handles unauthed) */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}