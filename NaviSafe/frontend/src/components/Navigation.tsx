import { NavLink, useLocation } from 'react-router-dom';
import { Activity, Compass, FileText, HeartPulse, Home, Shield, UserRound } from 'lucide-react';

const destinations = [
  { to: '/home', label: 'Home', icon: Home },
  { to: '/navigate', label: 'Navigate', icon: Compass },
  { to: '/analysis', label: 'Analysis', icon: Activity },
  { to: '/community', label: 'Community', icon: FileText },
  { to: '/check-in', label: 'Check-in', icon: HeartPulse },
  { to: '/profile', label: 'Profile', icon: UserRound },
];

export default function Navigation() {
  const location = useLocation();
  const publicPath = ['/', '/welcome', '/create-account', '/signin'].includes(location.pathname) || location.pathname.startsWith('/onboarding/');
  if (publicPath) return null;
  return (
    <nav className="app-nav" aria-label="Main navigation">
      <NavLink to="/home" className="brand" aria-label="SafePath home">
        <span className="brand-mark"><Shield size={20} strokeWidth={2.5} /></span>
        <span>SafePath</span>
      </NavLink>
      <div className="nav-links">
        {destinations.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} aria-label={label} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Icon size={20} strokeWidth={2} />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
      <div className="nav-footer">
        <span className="privacy-pill"><span className="status-dot" /> Local-first</span>
        <small>Safety tools, honest limits.</small>
      </div>
    </nav>
  );
}
