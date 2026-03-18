import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useMemo } from "react";
import { LayoutDashboard, Upload, History, BarChart2, Settings, LogOut, Zap, Sparkles } from "lucide-react";
import { useAuthStore } from "../../store/authStore";
import { logout } from "../../api/auth";
import toast from "react-hot-toast";

const NAV = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/agent",     icon: Sparkles,       label: "Agent" },
  { to: "/upload",    icon: Upload,          label: "Upload" },
  { to: "/history",   icon: History,         label: "History" },
  { to: "/analytics", icon: BarChart2,       label: "Analytics" },
  { to: "/settings",  icon: Settings,        label: "Settings" },
];

export default function Layout() {
  const { user, setUser } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // ignore
    }
    setUser(null);
    navigate("/login");
    toast.success("Logged out");
  };

  const displayName = useMemo(() => {
    if (!user) return "";
    return user.name?.split(" ")[0] ?? user.email;
  }, [user]);

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(236,72,153,0.2),transparent_55%),radial-gradient(circle_at_bottom,_rgba(99,102,241,0.2),transparent_55%),rgb(9,11,17)] lg:grid lg:h-screen lg:grid-cols-[280px_minmax(0,1fr)] lg:overflow-hidden">
      {/* Sidebar */}
      <aside className="relative border-b border-white/10 bg-white/5 backdrop-blur-xl shadow-[0_25px_60px_rgba(0,0,0,0.35)] lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r">
        <div className="flex flex-col gap-5 p-4 lg:h-full lg:overflow-y-auto lg:p-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl gradient-bg shadow-lg shadow-purple-500/30">
                <Zap size={20} className="text-white" />
              </div>
              <div>
                <p className="text-lg font-semibold tracking-tight text-white">ContentFlow</p>
                <p className="text-xs text-white/60">Modern content distribution</p>
              </div>
            </div>
          </div>
          <nav className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
            {NAV.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `shrink-0 whitespace-nowrap rounded-2xl px-4 py-3 text-sm font-semibold transition-all duration-200 ${
                    isActive
                      ? "bg-white/15 text-white shadow-[0_10px_30px_rgba(255,255,255,0.12)]"
                      : "text-white/70 hover:bg-white/10 hover:text-white"
                  } flex items-center gap-3`
                }
              >
                <Icon size={18} />
                {label}
              </NavLink>
            ))}
          </nav>
          {user && (
            <div className="flex items-center gap-3 rounded-2xl bg-white/5 p-3 lg:mt-auto">
              <div className="relative">
                <img
                  src={
                    user.avatar_url ||
                    `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name)}`
                  }
                  className="h-10 w-10 rounded-2xl border border-white/15 object-cover"
                  alt={user.name}
                />
                <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-[#090b11]" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-white">{displayName}</p>
                <p className="truncate text-xs text-white/50">{user.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="rounded-full p-2 text-white/70 transition hover:bg-white/10 hover:text-white"
                title="Log out"
              >
                <LogOut size={16} />
              </button>
            </div>
          )}
        </div>
      </aside>
      <main className="relative min-h-[calc(100vh-10rem)] p-4 lg:h-screen lg:overflow-y-auto lg:p-8">
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
