import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Loader from '../components/UI/Loader';
import toast from 'react-hot-toast';

const AuthCallback = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    const hash = window.location.hash.startsWith('#')
      ? window.location.hash.slice(1)
      : window.location.hash;
    const params = new URLSearchParams(hash);
    const token = params.get('access_token');

    if (token) {
      login(token);
      // Clear token from the URL
      window.history.replaceState(null, '', '/auth/callback');
      toast.success('Welcome to Synapse!');
      navigate('/', { replace: true });
    } else {
      toast.error('Login failed. Please try again with your IITD account.');
      navigate('/', { replace: true });
    }
  }, [login, navigate]);

  return (
    <div className="d-flex justify-content-center align-items-center vh-100">
      <div className="text-center">
        <Loader />
        <p className="mt-3 text-white">Verifying with IIT Delhi...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
