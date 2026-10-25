import { useEffect, useState } from 'react';
import { AlertTriangle, Download, Phone, RefreshCw, Shield } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Modal, Notice } from './Shared';
import { drafts, readLocal, requestLocation, syncDrafts } from '../services';
import type { Contact } from '../services';
import { checkInPhase } from '../checkin';

type InstallEvent = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };
export function SystemTools() {
  const [offline, setOffline] = useState(!navigator.onLine), [install, setInstall] = useState<InstallEvent | null>(null);
  const [update, setUpdate] = useState<ServiceWorker | null>(null), [pending, setPending] = useState(0), [low, setLow] = useState(false);
  const [error, setError] = useState('');
  const [checkin, setCheckin] = useState<{ destination: string; deadline: number } | null>(null);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const reconcile = () => {
      const saved = readLocal<{ destination: string; deadline: number } | null>('safepath-active-checkin', null);
      setCheckin(saved); setNow(Date.now());
      if (saved && saved.deadline <= Date.now() &&
        readLocal('safepath-privacy', { notifications: false }).notifications &&
        'Notification' in window && Notification.permission === 'granted' &&
        localStorage.getItem('safepath-notified') !== String(saved.deadline)) {
        try {
          new Notification('SafePath: time to check in', { body: 'Please confirm your arrival. No one has been contacted.' });
          localStorage.setItem('safepath-notified', String(saved.deadline));
        } catch { /* No delivery claim when the browser cannot display a notification. */ }
      }
    };
    const timer = window.setInterval(reconcile, 1000);
    document.addEventListener('visibilitychange', reconcile);
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', reconcile); };
  }, []);
  useEffect(() => {
    const refresh = () => { setOffline(!navigator.onLine); drafts().then(d => setPending(d.filter(x => x.state !== 'synced').length)).catch(e => setError(e.message)); };
    const online = () => { refresh(); void syncDrafts().catch(e => setError(e.message)); };
    const installer = (e: Event) => { e.preventDefault(); setInstall(e as InstallEvent); };
    const worker = (e: Event) => setUpdate((e as CustomEvent<ServiceWorker>).detail);
    window.addEventListener('online', online); window.addEventListener('offline', refresh);
    window.addEventListener('safepath-data', refresh); window.addEventListener('beforeinstallprompt', installer); window.addEventListener('safepath-update', worker);
    refresh(); void syncDrafts().catch(e => setError(e.message));
    const retry = window.setInterval(() => void syncDrafts().catch(e => setError(e.message)), 60000);
    type Battery = EventTarget & { level: number; charging: boolean };
    let battery: Battery | undefined;
    const batteryChange = () => { if (battery) setLow(battery.level <= .15 && !battery.charging); };
    const nav = navigator as Navigator & { getBattery?: () => Promise<Battery> };
    nav.getBattery?.().then(b => { battery = b; batteryChange(); b.addEventListener('levelchange', batteryChange); b.addEventListener('chargingchange', batteryChange); }).catch(() => {});
    if ('serviceWorker' in navigator) navigator.serviceWorker.getRegistration().then(r => { if (r?.waiting) setUpdate(r.waiting); });
    return () => { clearInterval(retry); window.removeEventListener('online', online); window.removeEventListener('offline', refresh); window.removeEventListener('safepath-data', refresh); window.removeEventListener('beforeinstallprompt', installer); window.removeEventListener('safepath-update', worker); battery?.removeEventListener('levelchange', batteryChange); battery?.removeEventListener('chargingchange', batteryChange); };
  }, []);
  return <>{checkin && checkInPhase(checkin.deadline, now) !== 'active' && <Notice tone="warning">{now < checkin.deadline ? 'Your arrival time is approaching.' : 'Your check-in is overdue. No one has been contacted automatically.'} <Link to="/check-in">Review arrival at {checkin.destination}</Link></Notice>}{offline && <Notice tone="warning">Offline · saved drafts and the app shell remain available. Live reports, map tiles and new routes may be unavailable.</Notice>}{low && <Notice tone="warning">Low battery · consider contacting someone now. Tracking may stop when this device sleeps.</Notice>}{error && <Notice tone="error">{error}</Notice>}<div className="system-bar"><span><Shield size={14} /> Delhi research prototype · synthetic route estimates</span><div>{pending > 0 && <Link to="/community/contributions">{pending} local items</Link>}{install && <button onClick={async () => { await install.prompt(); await install.userChoice; setInstall(null); }}><Download size={14} /> Install</button>}{update && <button onClick={() => { if (readLocal('safepath-active-checkin', null) || sessionStorage.getItem('safepath-active-route')) { setError('Finish your active journey or check-in before updating. Save any open report as a draft.'); return; } setError('Update ready. Save any open form, then use “Apply update” below.'); }}><RefreshCw size={14} /> Update ready</button>}{update && error.startsWith('Update ready') && <button onClick={() => { if (readLocal('safepath-active-checkin', null) || sessionStorage.getItem('safepath-active-route')) { setError('Finish your active journey or check-in before updating.'); return; } update.postMessage({ type: 'SKIP_WAITING' }); }}>Apply update</button>}</div></div></>;
}
export function EmergencyButton() {
  const [open, setOpen] = useState(false), [message, setMessage] = useState(''), [location, setLocation] = useState('');
  const contacts = readLocal<Contact[]>('safepath-contacts', []);
  return <><button className="emergency-fab" onClick={() => setOpen(true)}><AlertTriangle size={17} /> Get help</button>{open && <Modal title="Take the next step" close={() => setOpen(false)}><p>If you feel in danger, move toward a public place if you can. Choose an action below.</p><a className="button danger-button" href="tel:112"><Phone size={18} /> Open emergency call · 112</a><p className="small-note">Opens your dialer where supported. SafePath cannot confirm a call connected.</p><div className="contact-list">{contacts.map(c => <a className="contact-row" key={c.id} href={`tel:${c.phone.replace(/[^+0-9]/g, '')}`}><Phone size={17} /><span>{c.name}<small>{c.phone}</small></span></a>)}</div>{!contacts.length && <Link to="/onboarding/contacts" onClick={() => setOpen(false)}>Add a trusted contact</Link>}<button className="button button-quiet" onClick={async () => { try { const p = await requestLocation(); setLocation(`https://www.openstreetmap.org/?mlat=${p.coords.latitude.toFixed(4)}&mlon=${p.coords.longitude.toFixed(4)}#map=16/${p.coords.latitude.toFixed(4)}/${p.coords.longitude.toFixed(4)}`); setMessage(`Location captured ${new Date(p.timestamp).toLocaleTimeString()} · accuracy ±${Math.round(p.coords.accuracy)} m. Nothing shared yet.`); } catch (e) { setMessage((e as Error).message); } }}>Get location to share</button>{location && <><a href={location} target="_blank" rel="noreferrer">View captured location</a><button className="button button-quiet" onClick={async () => { try { if (navigator.share) { await navigator.share({ title: 'My location', text: 'Please check in with me.', url: location }); setMessage('Handed to the share sheet. Delivery is not confirmed.'); } else { await navigator.clipboard.writeText(location); setMessage('Location link copied. Send it to someone you trust.'); } } catch { setMessage('Sharing was cancelled or unavailable. You can copy the location link manually.'); } }}>Share captured location</button></>}{message && <Notice>{message}</Notice>}<Notice tone="warning">Automatic calls, SMS and community emergency alerts are not connected. No one has been notified.</Notice></Modal>}</>;
}
