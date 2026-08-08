import React from 'react';
import { X } from 'lucide-react';

const LoginModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const handleIitdLogin = () => {
    // Backend handles PKCE + redirect to DevClub OIDC (IIT Delhi)
    window.location.href = '/api/auth/login';
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="login-glass-container" onClick={e => e.stopPropagation()}>

        <button className="close-modal-btn" onClick={onClose}>
          <X size={24} />
        </button>

        <div className="login-brand-side">
          <div className="brand-content">
            <div className="synapse-logo">SYNAPSE</div>
            <h1>Welcome to Synapse</h1>
            <p>Your complete event management software solution</p>
          </div>
        </div>

        <div className="login-form-side">
          <div className="form-wrapper">
            <h2 className="fw-bold mb-2" style={{ color: 'var(--text-primary)' }}>Sign In</h2>
            <p className="mb-5" style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Use your IIT Delhi account to continue
            </p>

            <button className="btn-microsoft-login" onClick={handleIitdLogin}>
              Sign in with IIT Delhi
            </button>

            <p className="mt-4 text-center" style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
              Authenticated via DevClub OIDC (@iitd.ac.in)
            </p>
          </div>
        </div>

      </div>
    </div>
  );
};

export default LoginModal;
