import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ArrowRight, Eye, EyeOff, Lock, Mail } from 'lucide-react';
import AuthShell from '../components/AuthShell';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await register(email, password);
      navigate('/');
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join('. '));
      } else {
        setError('Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      eyebrow="Create Your Space"
      title="Start with a fresh workspace"
      subtitle="Create an account to save conversations, revisit outputs, and turn prompts into reusable project files."
      footerPrompt="Already have an account?"
      footerLinkLabel="Sign in"
      footerTo="/login"
    >
      <div className="auth-header">
        <p>Set up your account and begin chatting in minutes.</p>
      </div>

      {error && <div className="auth-error">{error}</div>}

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="input-group">
          <Mail size={18} className="input-icon" />
          <input
            id="register-email"
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
            id="register-password"
            type={showPassword ? 'text' : 'password'}
            placeholder="Password (min 8 chars, upper+lower+digit)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
          <button
            type="button"
            className="password-toggle"
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>

        <div className="input-group">
          <Lock size={18} className="input-icon" />
          <input
            id="register-confirm-password"
            type={showPassword ? 'text' : 'password'}
            placeholder="Confirm password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            autoComplete="new-password"
          />
        </div>

        <button
          id="register-submit"
          type="submit"
          className="auth-btn"
          disabled={loading}
        >
          {loading ? (
            <span className="btn-loading" />
          ) : (
            <>
              Create account
              <ArrowRight size={18} />
            </>
          )}
        </button>
      </form>
    </AuthShell>
  );
}
