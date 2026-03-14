import axios from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "../store/authStore";

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// ── Request interceptor — attach Bearer token from memory ─────────────────
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor — handle 401s ────────────────────────────────────
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

function processQueue(error: unknown) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(undefined);
  });
  failedQueue = [];
}

// Endpoints that must NEVER trigger the auto-refresh logic.
// ⚠️  /auth/refresh MUST be here — without it, the interceptor intercepts its
//     own refresh attempt when it gets a 401, pushes it onto failedQueue, and
//     creates a deadlock where the queue waits for a response that's IN the queue.
const SKIP_REFRESH = [
  "/auth/login",
  "/auth/register",
  "/auth/refresh",       // ← THE CRITICAL FIX: was missing, caused the deadlock
  "/auth/logout",
  "/auth/google/url",
  "/auth/google/callback",
  // NOTE: /auth/me is intentionally NOT here — we want 401s from /auth/me
  // to trigger a refresh attempt so session restoration works correctly.
];

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const status = error.response?.status;
    const originalReq = error.config;

    const shouldSkip = SKIP_REFRESH.some((p) =>
      originalReq?.url?.includes(p)
    );

    if (status === 401 && !originalReq?._retry && !shouldSkip) {
      // Another refresh already in-flight — queue this request.
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => api(originalReq))
          .catch((err) => Promise.reject(err));
      }

      originalReq._retry = true;
      isRefreshing = true;

      try {
        // Use a raw fetch here — NOT api.post() — so this call is completely
        // outside the interceptor and cannot be caught or queued again.
        const refreshResp = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });

        if (!refreshResp.ok) {
          // Refresh token invalid/expired — treat as a clean logout.
          throw new Error("refresh_failed");
        }

        const data = await refreshResp.json();

        if (data.access_token) {
          useAuthStore.getState().setAccessToken(data.access_token);
          originalReq.headers.Authorization = `Bearer ${data.access_token}`;
        }

        processQueue(null);
        isRefreshing = false;
        return api(originalReq);           // retry the original request
      } catch (refreshError) {
        processQueue(refreshError);
        isRefreshing = false;

        // Only log out if this was a genuine auth failure (refresh expired).
        // Don't call logout() for network errors — user might just be offline.
        const isAuthFailure =
          (refreshError as Error)?.message === "refresh_failed" ||
          (refreshError as any)?.response?.status === 401;

        if (isAuthFailure) {
          useAuthStore.getState().logout();
        }

        return Promise.reject(refreshError);
      }
    }

    // Show toast for non-401 errors (don't toast on expected 401 auth checks).
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      "Something went wrong";

    if (status && status !== 401) {
      toast.error(message);
    }

    return Promise.reject(error);
  }
);

export default api;