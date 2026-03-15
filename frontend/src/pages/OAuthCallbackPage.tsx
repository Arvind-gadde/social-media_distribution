import { useEffect, useRef } from "react";
import toast from "react-hot-toast";
import { useNavigate, useSearchParams } from "react-router-dom";
import api from "../api/client";
import { useAuthStore } from "../store/authStore";

export default function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setUser = useAuthStore((state) => state.setUser);
  const setAccessToken = useAuthStore((state) => state.setAccessToken);
  const setLoading = useAuthStore((state) => state.setLoading);
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
      toast.error("Invalid callback: missing code or state.");
      navigate("/login");
      return;
    }

    setLoading(true);

    api
      .get("/auth/google/callback", { params: { code, state } })
      .then((response: any) => {
        if (response.data.access_token) setAccessToken(response.data.access_token);
        setUser(response.data.user);
        toast.success(`Welcome, ${response.data.user.name}!`);
        navigate("/dashboard", { replace: true });
      })
      .catch((err) => {
        const message =
          err.response?.data?.detail ||
          err.response?.data?.message ||
          "Authentication failed. Please try again.";
        toast.error(message);
        navigate("/login", { replace: true });
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="space-y-4 text-center">
        <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
        <p className="text-sm text-white/[0.55]">Signing you in with Google...</p>
      </div>
    </div>
  );
}
