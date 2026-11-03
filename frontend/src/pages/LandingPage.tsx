import { useEffect, useState } from 'react';
import { ArrowDown, ArrowRight, Check, ChevronRight, Compass, HeartPulse, Menu, MessageCircle, ShieldCheck, Sparkles, X } from 'lucide-react';
import { Link } from 'react-router-dom';

type PreviewMode = 'route' | 'checkin' | 'community';

const previewContent: Record<PreviewMode, { label: string; title: string; detail: string; color: string }> = {
  route: { label: 'ROUTE CONTEXT', title: 'A route with more context', detail: '18 min · 1.4 km · updated 4 min ago', color: '#4d9b70' },
  checkin: { label: 'PRIVATE CHECK-IN', title: 'A quiet arrival reminder', detail: 'Set a deadline · choose who knows · stay in control', color: '#8572b7' },
  community: { label: 'LOCAL SIGNALS', title: 'Useful things people noticed', detail: 'Illustrative preview · no live observations', color: '#3984a3' },
};

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [preview, setPreview] = useState<PreviewMode>('route');
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 18);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const activePreview = previewContent[preview];

  return (
    <div className="landing-page">
      <header className={`landing-nav ${scrolled ? 'landing-nav-scrolled' : ''}`}>
        <Link className="brand landing-brand" to="/" onClick={() => setMenuOpen(false)}>
          <span className="brand-mark"><ShieldCheck size={20} /></span>SafePath
        </Link>
        <nav className={`landing-links ${menuOpen ? 'landing-links-open' : ''}`} aria-label="Landing page navigation">
          <a href="#how-it-works" onClick={() => setMenuOpen(false)}>How it works</a>
          <a href="#built-for-real-life" onClick={() => setMenuOpen(false)}>Why SafePath</a>
          <a href="#privacy" onClick={() => setMenuOpen(false)}>Privacy</a>
          <div className="mobile-menu-actions"><Link className="nav-login" to="/signin">Sign in</Link><Link className="button button-small" to="/create-account">Create local profile <ArrowRight size={15} /></Link></div>
        </nav>
        <div className="landing-nav-actions"><Link className="nav-login" to="/signin">Sign in</Link><Link className="button button-small" to="/create-account">Create local profile <ArrowRight size={15} /></Link></div>
        <button className="landing-menu-button" type="button" aria-label={menuOpen ? 'Close menu' : 'Open menu'} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={21} /> : <Menu size={21} />}</button>
      </header>

      <main>
        <section className="landing-hero landing-hero-new">
          <div className="landing-hero-copy landing-reveal">
            <span className="soft-label"><span className="pulse-dot" /> A calmer way to move through the city</span>
            <h1>Make your next journey feel a little more <em>thoughtful.</em></h1>
            <p>SafePath helps you understand your options, keep trusted people in the loop, and contribute what you notice along the way.</p>
            <div className="landing-cta"><Link className="button button-large" to="/create-account">Start your setup <ArrowRight size={17} /></Link><a className="scroll-link" href="#how-it-works"><span className="scroll-link-icon"><ArrowDown size={14} /></span> See how it works</a></div>
            <div className="landing-proof"><span><Check size={14} /> Works on your phone and desktop</span><span><Check size={14} /> You decide what to share</span></div>
          </div>
          <div className="landing-hero-art landing-reveal-delay" aria-label="Interactive SafePath preview">
            <div className="art-glow" />
            <div className="preview-shell">
              <div className="preview-toolbar"><span className="preview-brand"><span className="preview-brand-dot">S</span> SafePath</span><span className="preview-toolbar-status"><span className="status-dot" /> Ready to help</span></div>
              <div className="preview-canvas">
                <div className="preview-canvas-copy"><small>GOOD EVENING, TRAVELLER</small><strong>Where are you<br />heading?</strong><span>Plan with context before you leave.</span></div>
                <span className="canvas-line canvas-line-one" /><span className="canvas-line canvas-line-two" /><span className="canvas-line canvas-line-three" />
                <span className="canvas-node canvas-node-one" /><span className="canvas-node canvas-node-two" />
                <div className="preview-route-sheet" style={{ borderTopColor: activePreview.color }}><small>{activePreview.label}</small><strong>{activePreview.title}</strong><span>{activePreview.detail}</span><div className="preview-progress"><i style={{ background: activePreview.color }} /></div></div>
              </div>
              <div className="preview-tabs">{(['route', 'checkin', 'community'] as PreviewMode[]).map((item) => <button type="button" className={preview === item ? 'active' : ''} onClick={() => setPreview(item)} key={item}>{item === 'route' ? <Compass size={14} /> : item === 'checkin' ? <HeartPulse size={14} /> : <MessageCircle size={14} />} {item === 'route' ? 'Plan a route' : item === 'checkin' ? 'Check in' : 'Community'}</button>)}</div>
            </div>
            <div className="floating-note floating-note-top"><span className="floating-note-icon"><ShieldCheck size={15} /></span><span><strong>Control stays with you</strong><small>Clear choices, no silent sharing</small></span></div>
            <div className="floating-note floating-note-bottom"><span className="floating-avatar">P</span><span><strong>Trusted contact</strong><small>Only when you choose</small></span><span className="floating-check"><Check size={13} /></span></div>
          </div>
        </section>

        <section className="landing-trust-strip" aria-label="SafePath principles"><span>DESIGNED FOR REAL-LIFE MOMENTS</span><i /><strong>Plan</strong><i /><strong>Check in</strong><i /><strong>Share wisely</strong><i /><strong>Stay informed</strong></section>

        <section className="landing-story" id="how-it-works">
          <div className="landing-section-heading landing-section-heading-left"><p className="eyebrow">HOW SAFEPATH FITS IN</p><h2>Three small moments.<br /><em>One calmer journey.</em></h2><p>Use only the parts that are useful to you. SafePath is designed to support your decisions, not make promises on your behalf.</p></div>
          <div className="story-steps"><StoryStep number="01" icon={<Compass />} title="Before you go" text="Compare available routes and see the signals behind them." /><StoryStep number="02" icon={<HeartPulse />} title="While you travel" text="Set a private check-in and keep an arrival reminder close." /><StoryStep number="03" icon={<MessageCircle />} title="After you arrive" text="Share a useful observation only if you want to." /></div>
        </section>

        <section className="landing-values" id="built-for-real-life">
          <div className="landing-values-visual"><div className="values-orbit values-orbit-one" /><div className="values-orbit values-orbit-two" /><div className="values-center"><ShieldCheck size={28} /><span>your<br />control</span></div><span className="values-chip chip-one">Clear</span><span className="values-chip chip-two">Private</span><span className="values-chip chip-three">Honest</span></div>
          <div className="landing-values-copy"><p className="eyebrow">BUILT FOR REAL LIFE</p><h2>Helpful, without pretending to be a guarantee.</h2><p>Safety is personal and context changes quickly. That is why SafePath shows what it knows, what it does not know, and what will happen before a high-impact action.</p><ul><li><span><Check size={14} /></span><div><strong>See the reason</strong><small>Understand route signals instead of receiving a mysterious score.</small></div></li><li><span><Check size={14} /></span><div><strong>Choose the audience</strong><small>Keep preferences and check-ins private until you decide otherwise.</small></div></li><li><span><Check size={14} /></span><div><strong>Know the limits</strong><small>Browser permissions and background delivery are explained plainly.</small></div></li></ul></div>
        </section>

        <section className="landing-final-cta" id="privacy"><div><span className="soft-label"><Sparkles size={14} /> Start small</span><h2>Your next journey can begin with one clear choice.</h2><p>Create a local profile and make SafePath fit the way you move.</p></div><Link className="button button-large" to="/create-account">Create a local profile <ArrowRight size={17} /></Link></section>
        <footer className="landing-footer"><Link className="brand landing-brand" to="/"><span className="brand-mark"><ShieldCheck size={17} /></span>SafePath</Link><span>Planning and communication tools for more informed journeys.</span><Link to="/signin">Sign in <ChevronRight size={14} /></Link></footer>
      </main>
    </div>
  );
}

function StoryStep({ number, icon, title, text }: { number: string; icon: React.ReactNode; title: string; text: string }) {
  return <article className="story-step"><div className="story-step-top"><span className="story-number">{number}</span><span className="story-icon">{icon}</span></div><h3>{title}</h3><p>{text}</p></article>;
}

