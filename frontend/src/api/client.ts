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

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const status = error.response?.status;
    const originalReq = error.config;
    const isAuthEndpoint = originalReq?.url?.includes("/auth/");

    if (status === 401 && !originalReq?._retry && !isAuthEndpoint) {
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
        const { data } = await api.post("/auth/refresh");
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
        useAuthStore.getState().logout();
        return Promise.reject(refreshError);
      }
    }

    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      "Something went wrong";
    if (status && status !== 401) toast.error(message);

    return Promise.reject(error);
  }
);

export default api;