// frontend/vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react() // This plugin should handle .jsx and .tsx files correctly by default
  ]
  // NO 'esbuild' block here.
});