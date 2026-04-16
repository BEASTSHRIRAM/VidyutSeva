/**
 * AuthModal - Phone + OTP login.
 * Parchment design system, zero emojis.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { sendOTP, verifyOTP } from '../api';

export default function AuthModal({ onClose, onLoginSuccess }) {
  const [step, setStep] = useState('phone');
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [name, setName] = useState('');
  const [devOtp, setDevOtp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSendOTP = async (e) => {
    e.preventDefault();
    setError('');
    if (!/^\d{10}$/.test(phone.replace(/\s/g, ''))) { setError('Enter a valid 10-digit phone number'); return; }
    setLoading(true);
    try {
      const resp = await sendOTP(phone);
      if (resp.otp) setDevOtp(resp.otp);
      setStep('otp');
    } catch (err) { setError(err.message || 'Failed to send OTP'); }
    finally { setLoading(false); }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const resp = await verifyOTP(phone, otp, name || undefined);
      localStorage.setItem('vs_token', resp.access_token);
      localStorage.setItem('vs_user', JSON.stringify(resp.user));
      onLoginSuccess(resp.user);
      onClose();
    } catch (err) { setError(err.message || 'Invalid OTP'); }
    finally { setLoading(false); }
  };

  return (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        style={{ position: 'fixed', inset: 0, zIndex: 1000,
          background: 'rgba(20,20,19,0.55)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}
        onClick={(e) => e.target === e.currentTarget && onClose()}>
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 10 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          style={{ background: '#faf9f5', border: '1px solid #e8e6dc', borderRadius: 16,
            padding: 32, width: '100%', maxWidth: 400,
            boxShadow: 'rgba(0,0,0,0.12) 0px 24px 60px',
            fontFamily: "'Inter', sans-serif" }}>

          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: 28 }}>
            <div style={{ width: 48, height: 48, borderRadius: 12, background: '#c96442',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 16, fontWeight: 800, color: '#faf9f5', margin: '0 auto 16px',
              boxShadow: '0 6px 20px rgba(201,100,66,0.2)' }}>VS</div>
            <h2 style={{ fontFamily: "'Georgia', serif", fontSize: 22, fontWeight: 500,
              color: '#141413', marginBottom: 6 }}>
              {step === 'phone' ? 'Login to VidyutSeva' : 'Enter OTP'}
            </h2>
            <p style={{ fontSize: 13, color: '#87867f' }}>
              {step === 'phone' ? 'Enter your mobile number to continue' : `OTP sent to +91 ${phone}`}
            </p>
          </div>

          {devOtp && (
            <div style={{ marginBottom: 16, padding: '10px 14px', borderRadius: 8,
              background: 'rgba(201,100,66,0.06)', border: '1px solid rgba(201,100,66,0.15)',
              fontSize: 13, color: '#c96442', fontWeight: 500, textAlign: 'center' }}>
              Dev mode OTP: <strong style={{ letterSpacing: 2 }}>{devOtp}</strong>
            </div>
          )}

          {error && (
            <div style={{ marginBottom: 14, padding: '10px 14px', borderRadius: 8,
              background: 'rgba(181,51,51,0.06)', border: '1px solid rgba(181,51,51,0.15)',
              fontSize: 13, color: '#b53333' }}>{error}</div>
          )}

          {step === 'phone' && (
            <form onSubmit={handleSendOTP}>
              <div className="form-group">
                <label className="form-label">Mobile Number</label>
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
                    color: '#87867f', fontSize: 14, fontWeight: 600 }}>+91</span>
                  <input className="form-input" type="tel" maxLength={10} placeholder="XXXXXXXXXX"
                    value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
                    style={{ paddingLeft: 48 }} autoFocus required />
                </div>
              </div>
              <button type="submit" className="btn btn-primary" disabled={loading}
                style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}>
                {loading ? 'Sending...' : 'Send OTP'}
              </button>
            </form>
          )}

          {step === 'otp' && (
            <form onSubmit={handleVerifyOTP}>
              <div className="form-group">
                <label className="form-label">6-Digit OTP</label>
                <input className="form-input" type="text" maxLength={6} placeholder="------"
                  value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                  style={{ textAlign: 'center', fontSize: 24, letterSpacing: 8, fontWeight: 700 }}
                  autoFocus required />
              </div>
              <div className="form-group">
                <label className="form-label">Your Name (optional)</label>
                <input className="form-input" type="text" placeholder="e.g. Ramesh"
                  value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <button type="submit" className="btn btn-primary" disabled={loading || otp.length < 6}
                style={{ width: '100%', justifyContent: 'center', marginTop: 4 }}>
                {loading ? 'Verifying...' : 'Verify and Login'}
              </button>
              <button type="button"
                onClick={() => { setStep('phone'); setOtp(''); setDevOtp(null); setError(''); }}
                style={{ width: '100%', marginTop: 10, background: 'none', border: 'none',
                  color: '#87867f', fontSize: 13, cursor: 'pointer' }}>
                Change number
              </button>
            </form>
          )}

          <p style={{ textAlign: 'center', fontSize: 12, color: '#b0aea5', marginTop: 20, lineHeight: 1.5 }}>
            Anonymous reports work without login.<br />Login required for upvoting and tracking.
          </p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
