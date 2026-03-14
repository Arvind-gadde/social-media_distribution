import { useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import toast from "react-hot-toast";
import api from "../api/client";

export default function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setLoading = useAuthStore((s) => s.setLoading);
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    const error = params.get("error");
    if (error) {
      toast.error("Google login was cancelled or failed.");
      navigate("/login");
      return;
    }

    const code = params.get("code");
    const state = params.get("state");

    if (!code || !state) {
      toast.error("Invalid callback — missing code or state.");
      navigate("/login");
      return;
    }

    setLoading(true);

    api
      .get("/auth/google/callback", { params: { code, state } })
      .then((r: any) => {
        if (r.data.access_token) setAccessToken(r.data.access_token);
        setUser(r.data.user);
        toast.success(`Welcome, ${r.data.user.name}!`);
        navigate("/dashboard", { replace: true });
      })
      .catch((err) => {
        const msg =
          err.response?.data?.detail ||
          err.response?.data?.message ||
          "Authentication failed. Please try again.";
        toast.error(msg);
        navigate("/login", { replace: true });
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="w-12 h-12 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto" />
        <p className="text-slate-500 text-sm">Signing you in with Google…</p>
      </div>
    </div>
  );
}