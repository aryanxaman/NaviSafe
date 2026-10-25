import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import 'leaflet/dist/leaflet.css';
import './index.css';
import App from './App';
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  let reloading = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (navigator.serviceWorker.controller && !reloading && sessionStorage.getItem('safepath-worker-loaded')) { reloading = true; window.location.reload(); }
    sessionStorage.setItem('safepath-worker-loaded','true');
  });
  if (navigator.serviceWorker.controller) sessionStorage.setItem('safepath-worker-loaded','true');
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').then(reg => {
    const announce = () => { if (reg.waiting) window.dispatchEvent(new CustomEvent('safepath-update',{detail:reg.waiting})); };
    announce();
    reg.addEventListener('updatefound', () => reg.installing?.addEventListener('statechange',announce));
  }).catch(() => { /* Browser may disable workers. Local drafts still work independently. */ }));
}
createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
