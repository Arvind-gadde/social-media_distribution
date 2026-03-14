import { useState } from "react";
import { getGoogleUrl } from "../api/auth";
import { Zap } from "lucide-react";

export default function LoginPage() {
  const [loading, setLoading] = useState(false);

  const handleGoogle = async () => {
    setLoading(true);
    try {
      const { data } = await getGoogleUrl();
      window.location.href = data.url;
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 via-purple-50 to-pink-50">
      <div className="w-full max-w-md animate-fade-in">
        <div className="card p-8 text-center space-y-6">
          {/* Logo */}
          <div className="flex flex-col items-center gap-3">
            <div className="w-14 h-14 gradient-bg rounded-2xl flex items-center justify-center shadow-lg">
              <Zap size={28} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-800">ContentFlow</h1>
              <p className="text-slate-500 text-sm mt-1">India's all-in-one content distribution platform</p>
            </div>
          </div>

          {/* Platforms preview */}
          <div className="flex justify-center gap-2 flex-wrap">
            {["📸","▶️","💼","👥","✖️","🎬","🎵","💬"].map((icon, i) => (
              <span key={i} className="w-9 h-9 bg-slate-100 rounded-xl flex items-center justify-center text-lg">
                {icon}
              </span>
            ))}
          </div>

          <div className="space-y-2 text-sm text-slate-500">
            <p>Post once. Reach 12+ platforms.</p>
            <p className="text-xs">Instagram · YouTube · Josh · Moj · ShareChat · Koo · LinkedIn · X and more</p>
          </div>

          <button
            onClick={handleGoogle}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 border-2 border-slate-200 hover:border-brand-300 bg-white hover:bg-brand-50 rounded-xl py-3 px-5 font-semibold text-slate-700 transition-all duration-150 active:scale-95 disabled:opacity-50"
          >
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            {loading ? "Redirecting..." : "Continue with Google"}
          </button>

          <p className="text-xs text-slate-400">
            By continuing, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
}