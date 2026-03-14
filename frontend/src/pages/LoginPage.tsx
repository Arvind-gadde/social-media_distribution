import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getGoogleUrl, loginWithPassword } from "../api/auth";
import { useAuthStore } from "../store/authStore";
import { Zap } from "lucide-react";
import toast from "react-hot-toast";

export default function LoginPage() {
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  const validate = (): boolean => {
    const e: typeof errors = {};
    if (!email.includes("@")) e.email = "Enter a valid email";
    if (!password) e.password = "Password is required";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    try {
      const { data } = await loginWithPassword({
        email: email.trim().toLowerCase(),
        password,
      });
      if (data.access_token) setAccessToken(data.access_token);
      setUser(data.user);
      toast.success(`Welcome back, ${data.user.name}!`);
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        "Invalid email or password.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    setGoogleLoading(true);
    try {
      const { data } = await getGoogleUrl();
      window.location.href = data.url;
    } catch {
      toast.error("Could not reach Google. Try again.");
      setGoogleLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 via-purple-50 to-pink-50 py-10 px-4">
      <div className="w-full max-w-md">
        <div className="card p-8 space-y-6">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 gradient-bg rounded-2xl flex items-center justify-center shadow-md mx-auto">
              <Zap size={24} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-800">ContentFlow</h1>
            <p className="text-slate-500 text-sm">India's all-in-one content distribution platform</p>
          </div>

          <form onSubmit={handleLogin} noValidate className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">Email</label>
              <input
                id="email" type="email" autoComplete="email" placeholder="you@example.com"
                value={email}
                onChange={(e) => { setEmail(e.target.value); if (errors.email) setErrors((er) => ({ ...er, email: undefined })); }}
                className={`w-full border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 transition ${errors.email ? "border-red-400 bg-red-50" : "border-slate-200 bg-white"}`}
              />
              {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email}</p>}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1">Password</label>
              <input
                id="password" type="password" autoComplete="current-password" placeholder="Your password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); if (errors.password) setErrors((er) => ({ ...er, password: undefined })); }}
                className={`w-full border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 transition ${errors.password ? "border-red-400 bg-red-50" : "border-slate-200 bg-white"}`}
              />
              {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password}</p>}
            </div>

            <button type="submit" disabled={loading}
              className="w-full btn-primary py-3 rounded-xl font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="relative">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200" /></div>
            <div className="relative flex justify-center"><span className="bg-white px-3 text-xs text-slate-400">or</span></div>
          </div>

          <button onClick={handleGoogle} disabled={googleLoading}
            className="w-full flex items-center justify-center gap-3 border-2 border-slate-200 hover:border-brand-300 bg-white hover:bg-brand-50 rounded-xl py-3 px-5 font-semibold text-slate-700 text-sm transition-all duration-150 active:scale-95 disabled:opacity-50">
            <GoogleIcon />
            {googleLoading ? "Redirecting…" : "Continue with Google"}
          </button>

          <p className="text-center text-sm text-slate-500">
            Don't have an account?{" "}
            <Link to="/register" className="text-brand-600 font-medium hover:underline">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  );
}