import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Don't retry on 401 — it will just hammer the backend and trigger
      // the refresh interceptor multiple times simultaneously.
      retry: (failureCount, error: any) => {
        if (error?.response?.status === 401) return false;
        return failureCount < 1;
      },
      staleTime: 30_000,
      // Don't refetch when window regains focus — avoids spurious 401s
      // when the user switches back from the terminal/browser devtools.
      refetchOnWindowFocus: false,
    },
    mutations: { retry: 0 },
  },
});

// StrictMode intentionally omitted in development — it double-invokes
// useEffect which fires two concurrent getMe() requests that race each
// other and can cause a false logout. Add it back for production builds
// once the auth flow is stable.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <App />
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
    </BrowserRouter>
  </QueryClientProvider>
);