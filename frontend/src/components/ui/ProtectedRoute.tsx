import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";

interface Props {
  children?: React.ReactNode;
}

export default function ProtectedRoute({ children }: Props) {
  const user = useAuthStore((s) => s.user);
  const isLoading = useAuthStore((s) => s.isLoading);

  // While checking session on initial load — show spinner
  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;

  // Supports both wrapper pattern (<ProtectedRoute><Layout /></ProtectedRoute>)
  // and outlet pattern (nested <Route> children)
  return children ? <>{children}</> : <Outlet />;
}