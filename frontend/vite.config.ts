import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API is proxied so cookies stay same-origin; production uses VITE_API_URL.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
