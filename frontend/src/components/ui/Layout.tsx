import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useMemo, useState, useEffect } from "react";
import {
  LayoutDashboard, Upload, History, BarChart2, Settings,
  LogOut, Zap, Sparkles, Flame, Menu, X,
} from "lucide-react";
import { useAuthStore } from "../../store/authStore";
import { logout } from "../../api/auth";
import toast from "react-hot-toast";

const NAV = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/agent",     icon: Sparkles,        label: "Agent"     },
  { to: "/insights",  icon: Flame,           label: "Insights"  },
  { to: "/upload",    icon: Upload,          label: "Upload"    },
  { to: "/history",   icon: History,         label: "History"   },
  { to: "/analytics", icon: BarChart2,       label: "Analytics" },
  { to: "/settings",  icon: Settings,        label: "Settings"  },
];

interface NavContentProps {
  onNavClick?: () => void;
}

function NavContent({ onNavClick }: NavContentProps) {
  const { user, setUser } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try { await logout(); } catch { /* ignore */ }
    setUser(null);
    navigate("/login");
    toast.success("Logged out");
    onNavClick?.();
  };

  const displayName = useMemo(() => {
    if (!user) return "";
    return user.name?.split(" ")[0] ?? user.email;
  }, [user]);

  return (
    <div className="flex h-full flex-col gap-6 overflow-y-auto px-4 py-5">
      {/* Brand */}
      <div className="flex items-center gap-3 px-1 shrink-0">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl gradient-bg shadow-lg shadow-purple-500/25 shrink-0">
          <Zap size={17} className="text-white" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-tight text-white leading-none">ContentFlow</p>
          <p className="text-[11px] text-white/45 mt-0.5">AI Content Distribution</p>
        </div>
      </div>

      {/* Nav links */}
      <nav className="flex flex-col gap-0.5">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavClick}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-white/10 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.07)]"
                  : "text-white/55 hover:bg-white/[0.07] hover:text-white"
              }`
            }
          >
            <Icon size={17} strokeWidth={1.8} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User footer */}
      {user && (
        <div className="mt-auto shrink-0 flex items-center gap-3 rounded-xl border border-white/[0.09] bg-white/[0.04] p-3">
          <div className="relative shrink-0">
            <img
              src={
                user.avatar_url ||
                `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}&background=6839d8&color=fff`
              }
              className="h-8 w-8 rounded-lg border border-white/15 object-cover"
              alt={user.name}
            />
            <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-[#090b11]" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-white leading-tight">{displayName}</p>
            <p className="truncate text-[11px] text-white/40 mt-0.5">{user.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-lg p-1.5 text-white/45 transition-all hover:bg-white/10 hover:text-white tap-target flex items-center justify-center"
            title="Log out"
          >
            <LogOut size={15} />
          </button>
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Close drawer on Escape key
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && mobileNavOpen) setMobileNavOpen(false);
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [mobileNavOpen]);

  // Prevent body scroll when mobile nav is open
  useEffect(() => {
    if (mobileNavOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [mobileNavOpen]);

  return (
    <div className="min-h-screen overflow-x-hidden lg:grid lg:h-screen lg:grid-cols-[256px_minmax(0,1fr)] lg:overflow-hidden"
      style={{
        backgroundImage: `
          radial-gradient(ellipse 80% 50% at 10% 5%, rgba(104,57,216,0.16), transparent),
          radial-gradient(ellipse 60% 40% at 90% 95%, rgba(236,72,153,0.12), transparent),
          linear-gradient(175deg, #07080f, #090b11 40%, #0b0d18)
        `,
      }}
    >
      {/* ── Mobile top bar (hidden on lg) ── */}
      <header className="sticky top-0 z-40 flex items-center justify-between px-4 py-3 border-b border-white/[0.09] bg-[#090b11]/85 backdrop-blur-xl lg:hidden">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl gradient-bg shadow-purple-500/25 shrink-0">
            <Zap size={15} className="text-white" />
          </div>
          <span className="text-sm font-bold text-white tracking-tight">ContentFlow</span>
        </div>
        <button
          onClick={() => setMobileNavOpen(true)}
          className="rounded-xl p-2 text-white/60 hover:bg-white/10 hover:text-white transition-all tap-target flex items-center justify-center"
          aria-label="Open navigation menu"
        >
          <Menu size={20} />
        </button>
      </header>

      {/* ── Mobile drawer overlay (hidden on lg) ── */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/65 backdrop-blur-sm animate-fade-in"
            onClick={() => setMobileNavOpen(false)}
          />
          {/* Drawer panel */}
          <aside
            className="absolute left-0 top-0 h-full w-[268px] border-r border-white/[0.09] animate-slide-in-left"
            style={{
              background: "linear-gradient(175deg, #0d0f1c, #090b15)",
              boxShadow: "4px 0 40px rgba(0,0,0,0.5)",
            }}
          >
            {/* Close button */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.07]">
              <div className="flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg gradient-bg shrink-0">
                  <Zap size={13} className="text-white" />
                </div>
                <span className="text-sm font-bold text-white">ContentFlow</span>
              </div>
              <button
                onClick={() => setMobileNavOpen(false)}
                className="rounded-lg p-1.5 text-white/50 hover:bg-white/10 hover:text-white transition-all tap-target flex items-center justify-center"
                aria-label="Close navigation"
              >
                <X size={18} />
              </button>
            </div>
            <NavContent onNavClick={() => setMobileNavOpen(false)} />
          </aside>
        </div>
      )}

      {/* ── Desktop sidebar (hidden below lg) ── */}
      <aside
        className="hidden lg:flex lg:flex-col border-r border-white/[0.09] lg:h-screen lg:overflow-hidden"
        style={{ background: "rgba(255,255,255,0.025)" }}
      >
        <NavContent />
      </aside>

      {/* ── Main content area ── */}
      <main className="relative min-w-0 overflow-x-hidden overflow-y-auto p-4 lg:h-screen lg:p-8">
        <div className="mx-auto min-w-0 max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
