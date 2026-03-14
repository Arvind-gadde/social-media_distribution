import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, Upload, History, BarChart2, Settings, LogOut, Zap } from "lucide-react";
import { useAuthStore } from "../../store/authStore";
import { logout } from "../../api/auth";
import toast from "react-hot-toast";

const NAV = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/upload",    icon: Upload,          label: "Upload" },
  { to: "/history",   icon: History,         label: "History" },
  { to: "/analytics", icon: BarChart2,       label: "Analytics" },
  { to: "/settings",  icon: Settings,        label: "Settings" },
];

export default function Layout() {
  const { user, setUser } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try { await logout(); } catch {}
    setUser(null);
    navigate("/login");
    toast.success("Logged out");
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-60 bg-white border-r border-slate-100 flex flex-col shadow-sm shrink-0">
        <div className="flex items-center gap-2.5 px-6 py-5 border-b border-slate-100">
          <div className="w-8 h-8 gradient-bg rounded-lg flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <span className="font-bold text-slate-800 text-lg">ContentFlow</span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                isActive
                  ? "bg-brand-50 text-brand-700"
                  : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
              }`
            }>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="p-3 border-t border-slate-100">
            <div className="flex items-center gap-3 px-3 py-2 rounded-xl">
              <img src={user.avatar_url || `https://ui-avatars.com/api/?name=${user.name}`}
                className="w-8 h-8 rounded-full object-cover" alt={user.name} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-700 truncate">{user.name}</p>
                <p className="text-xs text-slate-400 truncate">{user.email}</p>
              </div>
              <button onClick={handleLogout} className="text-slate-400 hover:text-red-500 transition-colors">
                <LogOut size={16} />
              </button>
            </div>
          </div>
        )}
      </aside>
      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}