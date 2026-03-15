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

// ⚠️  /auth/refresh MUST be in this list.
//
// Without it, the interceptor intercepts its own refresh call when that call
// gets a 401, pushes it onto failedQueue, and creates a deadlock:
//   – outer await api.post("/auth/refresh") waits for processQueue(null)
//   – processQueue(null) waits for the inner /auth/refresh to resolve
//   – inner /auth/refresh is sitting in failedQueue, waiting for processQueue
//   → nothing ever moves → setLoading(false) is never called → spinner forever
const SKIP_REFRESH = [
  "/auth/login",
  "/auth/register",
  "/auth/refresh",      // ← CRITICAL — prevents the deadlock described above
  "/auth/logout",
  "/auth/google/url",
  "/auth/google/callback",
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
      if (isRefreshing) {
        // Another refresh is in flight — queue this request until it resolves.
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => api(originalReq))
          .catch((err) => Promise.reject(err));
      }

      originalReq._retry = true;
      isRefreshing = true;

      try {
        // Use raw fetch — NOT api.post() — so this call is completely outside
        // the Axios interceptor chain and can never be caught or queued again.
        const refreshResp = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });

        if (!refreshResp.ok) {
          throw new Error("refresh_failed");
        }

        const data = await refreshResp.json();

        if (data.access_token) {
          useAuthStore.getState().setAccessToken(data.access_token);
          originalReq.headers.Authorization = `Bearer ${data.access_token}`;
        }

        processQueue(null);
        isRefreshing = false;
        return api(originalReq);
      } catch (refreshError) {
        processQueue(refreshError);
        isRefreshing = false;

        const isAuthFailure =
          (refreshError as Error)?.message === "refresh_failed" ||
          (refreshError as any)?.response?.status === 401;

        if (isAuthFailure) {
          useAuthStore.getState().logout();
        }

        return Promise.reject(refreshError);
      }
    }

    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      "Something went wrong";

    // Don't toast on expected 401 auth checks (e.g. /auth/me on page load).
    if (status && status !== 401) {
      toast.error(message);
    }

    return Promise.reject(error);
  }
);

export default api;