import { useState } from 'react';
import { ArrowRight, KeyRound, Lock, Mail, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import API from '../api/axios';
import AuthShell from '../components/AuthShell';

const initialResetForm = {
  email: '',
  otp: '',
  newPassword: '',
  confirmPassword: '',
};

export default function ForgotPassword() {
  const [requestEmail, setRequestEmail] = useState('');
  const [resetForm, setResetForm] = useState(initialResetForm);
  const [requestLoading, setRequestLoading] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [requestError, setRequestError] = useState('');
  const [resetError, setResetError] = useState('');
  const [requestSuccess, setRequestSuccess] = useState('');
  const [resetSuccess, setResetSuccess] = useState('');

  const handleRequestOtp = async (e) => {
    e.preventDefault();
    setRequestError('');
    setRequestSuccess('');
    setRequestLoading(true);

    try {
      const res = await API.post('/auth/forgot-password', { email: requestEmail });
      setRequestSuccess(
        res.data?.detail || 'If that email exists, an OTP has been sent to your inbox.'
      );
      setResetForm((prev) => ({ ...prev, email: requestEmail || prev.email }));
    } catch (err) {
      setRequestError(
        err.response?.data?.detail
        || 'Could not send an OTP yet. The backend recovery endpoint may still need to be added.'
      );
    } finally {
      setRequestLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setResetError('');
    setResetSuccess('');

    if (resetForm.newPassword !== resetForm.confirmPassword) {
      setResetError('New password and confirmation do not match.');
      return;
    }

    setResetLoading(true);

    try {
      const res = await API.post('/auth/reset-password', {
        email: resetForm.email,
        otp: resetForm.otp,
        new_password: resetForm.newPassword,
      });
      setResetSuccess(
        res.data?.detail || 'Password updated successfully. You can sign in now.'
      );
      setResetForm(initialResetForm);
    } catch (err) {
      setResetError(
        err.response?.data?.detail
        || 'Could not reset the password. Check the OTP and backend recovery setup.'
      );
    } finally {
      setResetLoading(false);
    }
  };

  return (
    <AuthShell
      eyebrow="Password Recovery"
      title="Recover your account"
      subtitle="Request a one-time code, then confirm it with a new password to get back into Gem-AI."
      footerPrompt="Remembered your password?"
      footerLinkLabel="Back to sign in"
      footerTo="/login"
    >
      <div className="auth-header">
        <p>Use your account email to receive an OTP and complete the reset flow.</p>
      </div>

      <div className="auth-stack">
        <section className="auth-section-card">
          <div className="auth-section-head">
            <div className="auth-section-icon">
              <Mail size={18} />
            </div>
            <div>
              <h3>1. Request OTP</h3>
              <p>We’ll send a one-time code to your email address.</p>
            </div>
          </div>

          {requestError && <div className="auth-error">{requestError}</div>}
          {requestSuccess && <div className="auth-success">{requestSuccess}</div>}

          <form onSubmit={handleRequestOtp} className="auth-form">
            <div className="input-group">
              <Mail size={18} className="input-icon" />
              <input
                type="email"
                placeholder="Email address"
                value={requestEmail}
                onChange={(e) => setRequestEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <button type="submit" className="auth-btn" disabled={requestLoading}>
              {requestLoading ? (
                <span className="btn-loading" />
              ) : (
                <>
                  Send OTP
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </section>

        <section className="auth-section-card">
          <div className="auth-section-head">
            <div className="auth-section-icon">
              <ShieldCheck size={18} />
            </div>
            <div>
              <h3>2. Reset with OTP</h3>
              <p>Enter the code and choose a new password.</p>
            </div>
          </div>

          {resetError && <div className="auth-error">{resetError}</div>}
          {resetSuccess && <div className="auth-success">{resetSuccess}</div>}

          <form onSubmit={handleResetPassword} className="auth-form">
            <div className="input-group">
              <Mail size={18} className="input-icon" />
              <input
                type="email"
                placeholder="Email address"
                value={resetForm.email}
                onChange={(e) => setResetForm((prev) => ({ ...prev, email: e.target.value }))}
                required
                autoComplete="email"
              />
            </div>

            <div className="input-group">
              <KeyRound size={18} className="input-icon" />
              <input
                type="text"
                placeholder="OTP code"
                value={resetForm.otp}
                onChange={(e) => setResetForm((prev) => ({ ...prev, otp: e.target.value }))}
                required
                inputMode="numeric"
              />
            </div>

            <div className="input-group">
              <Lock size={18} className="input-icon" />
              <input
                type="password"
                placeholder="New password"
                value={resetForm.newPassword}
                onChange={(e) => setResetForm((prev) => ({ ...prev, newPassword: e.target.value }))}
                required
                autoComplete="new-password"
              />
            </div>

            <div className="input-group">
              <Lock size={18} className="input-icon" />
              <input
                type="password"
                placeholder="Confirm new password"
                value={resetForm.confirmPassword}
                onChange={(e) => setResetForm((prev) => ({ ...prev, confirmPassword: e.target.value }))}
                required
                autoComplete="new-password"
              />
            </div>

            <button type="submit" className="auth-btn" disabled={resetLoading}>
              {resetLoading ? (
                <span className="btn-loading" />
              ) : (
                <>
                  Update password
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </section>
      </div>

      <div className="auth-helper-links">
        <Link to="/login">Return to sign in</Link>
        <Link to="/register">Need a new account?</Link>
      </div>
    </AuthShell>
  );
}
