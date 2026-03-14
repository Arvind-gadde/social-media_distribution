import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import toast from "react-hot-toast";
import api from "../api/client";

export default function OAuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);

  useEffect(() => {
    const error = params.get("error");
    if (error) {
      toast.error("Login failed. Please try again.");
      navigate("/login");
      return;
    }

    const code = params.get("code");
    const state = params.get("state");

    if (!code || !state) {
      toast.error("Invalid callback parameters");
      navigate("/login");
      return;
    }

    // Exchange code with backend
    api
      .get("/auth/google/callback", { params: { code, state } })
      .then((r: any) => {
        setUser(r.data.user);
        toast.success(`Welcome back, ${r.data.user.name}!`);
        // Small delay to allow cookies to be set
        setTimeout(() => navigate("/dashboard"), 500);
      })
      .catch((err) => {
        console.error("Auth error:", err);
        toast.error("Authentication failed");
        navigate("/login");
      });
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="w-12 h-12 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto" />
        <p className="text-slate-500">Signing you in…</p>
      </div>
    </div>
  );
}