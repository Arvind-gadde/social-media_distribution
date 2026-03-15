import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";

// ── DEV BYPASS ────────────────────────────────────────────────────────────
// Set this to true to skip all auth checks during development.
// Flip back to false before deploying to production.
const DEV_BYPASS_AUTH = true;
// ─────────────────────────────────────────────────────────────────────────

interface Props {
  children?: React.ReactNode;
}

export default function ProtectedRoute({ children }: Props) {
  const user = useAuthStore((s) => s.user);
  const isLoading = useAuthStore((s) => s.isLoading);

  // Dev bypass — skip all auth, render everything directly
  if (DEV_BYPASS_AUTH) {
    return children ? <>{children}</> : <Outlet />;
  }

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  return children ? <>{children}</> : <Outlet />;
}