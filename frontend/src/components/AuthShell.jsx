import { Link } from 'react-router-dom';
import { MessageSquareText, ShieldCheck, Sparkles, Wand2 } from 'lucide-react';

const highlights = [
  {
    icon: MessageSquareText,
    title: 'One place for every mode',
    description: 'Switch between general reasoning, coding help, and image generation without leaving the thread.',
  },
  {
    icon: Wand2,
    title: 'Built for project momentum',
    description: 'Turn prompts into structured code, downloadable ZIPs, and reusable conversations.',
  },
  {
    icon: ShieldCheck,
    title: 'Private workspace feel',
    description: 'Keep your chat history, account access, and AI workflow in a focused environment.',
  },
];

export default function AuthShell({
  eyebrow,
  title,
  subtitle,
  footerPrompt,
  footerLinkLabel,
  footerTo,
  children,
}) {
  return (
    <div className="auth-page">
      <div className="auth-noise" />

      <section className="auth-showcase">
        <div className="auth-brand">
          <div className="auth-brand-mark">
            <Sparkles size={18} />
          </div>
          <span>Gem-AI</span>
        </div>

        <div className="auth-copy">
          <p className="auth-eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>

        <div className="auth-stat-row">
          <div className="auth-stat-card">
            <strong>3 Modes</strong>
            <span>General, coding, image</span>
          </div>
          <div className="auth-stat-card">
            <strong>Persistent chats</strong>
            <span>Resume ideas whenever you need</span>
          </div>
        </div>

        <div className="auth-feature-list">
          {highlights.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.title} className="auth-feature-card">
                <div className="auth-feature-icon">
                  <Icon size={18} />
                </div>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.description}</p>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="auth-card-head">
            <div className="auth-logo">
              <Sparkles size={26} />
            </div>
            <div className="auth-card-copy">
              <p className="auth-card-kicker">{eyebrow}</p>
              <h2>{title}</h2>
            </div>
          </div>

          {children}

          <div className="auth-footer">
            <p>
              {footerPrompt}{' '}
              <Link to={footerTo}>{footerLinkLabel}</Link>
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
