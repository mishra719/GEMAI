import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ArrowRight, Eye, EyeOff, Lock, Mail } from 'lucide-react';
import AuthShell from '../components/AuthShell';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      eyebrow="Workspace Access"
      title="Welcome back"
      subtitle="Pick up your saved chats, ideas, and generated projects from a calmer AI workspace."
      footerPrompt="Don't have an account?"
      footerLinkLabel="Create one"
      footerTo="/register"
    >
      <div className="auth-header">
        <p>Sign in to continue building with Gem-AI.</p>
      </div>

      {error && <div className="auth-error">{error}</div>}

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="input-group">
          <Mail size={18} className="input-icon" />
          <input
            id="login-email"
            type="email"
            placeholder="Email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </div>

        <div className="input-group">
          <Lock size={18} className="input-icon" />
          <input
            id="login-password"
            type={showPassword ? 'text' : 'password'}
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          <button
            type="button"
            className="password-toggle"
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        <div className="auth-inline-actions">
          <Link to="/forgot-password" className="auth-text-link">
            Forgot password?
          </Link>
        </div>

        <button
          id="login-submit"
          type="submit"
          className="auth-btn"
          disabled={loading}
        >
          {loading ? (
            <span className="btn-loading" />
          ) : (
            <>
              Continue
              <ArrowRight size={18} />
            </>
          )}
        </button>
      </form>
    </AuthShell>
  );
}
