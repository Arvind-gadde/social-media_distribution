import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getMe } from "../api/auth";
import { useAuthStore } from "../store/authStore";
import toast from "react-hot-toast";

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
    getMe()
      .then((r) => {
        setUser(r.data.user);
        toast.success(`Welcome back, ${r.data.user.name}!`);
        navigate("/dashboard");
      })
      .catch(() => {
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