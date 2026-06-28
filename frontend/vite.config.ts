import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies API calls to the FastAPI backend so the app uses same-origin
// "/visualize" in both dev and prod. Backend default port for this project: 8077.
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: { outDir: "dist" },
  server: {
    port: 5173,
    proxy: {
      "/visualize": "http://localhost:8077",
      "/health": "http://localhost:8077",
    },
  },
});
