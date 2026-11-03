import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
export default defineConfig({
  plugins: [react(), {
    name: 'safepath-offline-shell',
    generateBundle(_options, bundle) {
      const assets = ['/index.html','/manifest.webmanifest','/favicon.svg','/icon-192.png','/icon-512.png', ...Object.keys(bundle).filter(k=>k.endsWith('.js')||k.endsWith('.css')).map(k=>'/'+k)];
      const version = createHash('sha256').update(JSON.stringify(assets)).digest('hex').slice(0,12);
      const source = readFileSync('public/sw.js','utf8').replace('__BUILD__',version).replace('__PRECACHE__',JSON.stringify(assets));
      this.emitFile({type:'asset',fileName:'sw.js',source});
    }
  }],
  server: {host:'127.0.0.1',proxy:{'/api':{target:'http://127.0.0.1:8000',changeOrigin:true}}},
  preview: {host:'127.0.0.1',proxy:{'/api':{target:'http://127.0.0.1:8000',changeOrigin:true}}},
});
