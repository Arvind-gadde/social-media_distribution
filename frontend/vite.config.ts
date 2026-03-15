import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: "0.0.0.0",   // needed so Docker can expose the port
    proxy: {
      "/api": {
        // When running in Docker, use the service name "backend"
        // NOT localhost — localhost inside the frontend container = frontend itself
        target: "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
});