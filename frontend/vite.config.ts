import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        // changeOrigin rewrites the Host header so the backend accepts it.
        // Do NOT set cookieDomainRewrite — it adds Domain=localhost to
        // Set-Cookie headers, which Chrome silently drops.
        changeOrigin: true,
      },
    },
  },
});