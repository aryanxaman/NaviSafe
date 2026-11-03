import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ShieldCheck, X } from 'lucide-react';
import { api, statusLabel } from '../services';
import type { CommunityReport } from '../services';

export function PageHeader({ eyebrow, title, text, action }: { eyebrow: string; title: string; text: string; action?: ReactNode }) {
  return <header className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="lede">{text}</p></div>{action}</header>;
}
export function Notice({ children, tone = '' }: { children: ReactNode; tone?: string }) {
  return <div className={`notice ${tone}`} role={tone === 'error' ? 'alert' : 'status'}>{children}</div>;
}
export function Modal({ title, children, close }: { title: string; children: ReactNode; close: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement;
    ref.current?.showModal();
    return () => { previous?.focus(); };
  }, []);
  return <dialog ref={ref} className="sp-dialog" onCancel={e => { e.preventDefault(); close(); }}><div className="card-heading"><h2>{title}</h2><button className="icon-button" aria-label="Close dialog" onClick={close}><X /></button></div>{children}</dialog>;
}
export function ReportCard({ report, mine = false }: { report: CommunityReport; mine?: boolean }) {
  const [open, setOpen] = useState(false), [kind, setKind] = useState('inaccurate'), [reason, setReason] = useState(''), [message, setMessage] = useState('');
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 60000); return () => clearInterval(timer); }, []);
  const stale = Date.parse(report.expires_at) <= now;
  return <article className="report-card"><div className="card-heading"><span className={`evidence-badge ${report.status}`}>{stale ? 'Expired' : statusLabel[report.status] || report.status}</span><small>User observation</small></div><h3>{report.street}</h3><p className="report-category">{report.category.replaceAll('_', ' ')}</p><p>{report.description || 'No additional description provided.'}</p><div className="report-meta"><span>Observed {new Date(report.observed_at).toLocaleString()}</span><span>Submitted {new Date(report.submitted_at).toLocaleString()}</span></div><button className="text-button" onClick={() => setOpen(true)}>{mine ? 'Correct or appeal' : 'Request a review'} <ArrowUpRight size={14} /></button>{open && <Modal title="Help keep this accurate" close={() => setOpen(false)}><form onSubmit={async e => { e.preventDefault(); try { await api(`/reports/${report.id}/review`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ kind, reason }) }); setMessage('Request received for human review. No evidence status was changed automatically.'); } catch (err) { setMessage((err as Error).message); } }}><label>Reason for review<select value={kind} onChange={e => setKind(e.target.value)}><option value="inaccurate">Information may be inaccurate</option><option value="resolved">Hazard no longer present</option><option value="abuse">Report abuse</option>{mine && <><option value="correction">Correct my observation</option><option value="appeal">Appeal the decision</option></>}</select></label><label>Factual details<textarea required minLength={12} maxLength={1000} value={reason} onChange={e => setReason(e.target.value)} /></label><button className="button">Request review</button>{message && <Notice>{message}</Notice>}</form></Modal>}</article>;
}
export function EvidenceNote() {
  return <div className="trust-note"><ShieldCheck size={18} /><span>Images support a report; they do not prove it. <Link to="/profile/help">Understand evidence labels</Link></span></div>;
}
