import axios from "axios";
import toast from "react-hot-toast";

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

let isRefreshing = false;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const status = error.response?.status;
    const originalReq = error.config;

    if (status === 401 && !originalReq._retry && !originalReq.url?.includes("/auth/")) {
      if (isRefreshing) return Promise.reject(error);
      isRefreshing = true;
      originalReq._retry = true;
      try {
        await api.post("/auth/refresh");
        isRefreshing = false;
        return api(originalReq);
      } catch {
        isRefreshing = false;
        window.location.href = "/login";
        return Promise.reject(error);
      }
    }

    const message = error.response?.data?.message || "Something went wrong";
    if (status !== 401) toast.error(message);
    return Promise.reject(error);
  }
);

export default api;