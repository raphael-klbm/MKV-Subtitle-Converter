// vite.config.js
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  root: '.', // Projekt-Wurzel (wo index.html liegt)
  server: {
    port: 5173,        // optional: Port fürs Dev-Frontend
    open: true,         // Browser automatisch öffnen
    proxy: {
      // Proxy API requests to the Flask backend
      '/version': 'http://127.0.0.1:5000',
      '/theme': 'http://127.0.0.1:5000',
      '/checkForUpdate': 'http://127.0.0.1:5000',
      '/upload': 'http://127.0.0.1:5000',
      '/convert': 'http://127.0.0.1:5000',
      '/userLanguages': 'http://127.0.0.1:5000',
      '/isoCodes': 'http://127.0.0.1:5000',
      '/userSettings': 'http://127.0.0.1:5000',
      '/files': 'http://127.0.0.1:5000',
      '/conversionStatus': 'http://127.0.0.1:5000',
      '/cancelConversion': 'http://127.0.0.1:5000'
    }
  },
  build: {
    outDir: 'dist',    // Build-Ordner
    emptyOutDir: true
  }, plugins: [
    tailwindcss()
    ]
});