/**
 * VapiWidget - Web SDK Voice Call Button
 * Allows direct browser calls to the Vapi Assistant.
 */
import { useEffect, useState, useRef } from 'react';
import Vapi from '@vapi-ai/web';

export default function VapiWidget() {
  const [callStatus, setCallStatus] = useState('inactive'); // 'inactive', 'loading', 'active'
  const vapiRef = useRef(null);

  useEffect(() => {
    // Initialize Vapi SDK. We use VITE_VAPI_PUBLIC_KEY or a hardcoded token.
    // Replace the fallback with your actual Public API Key from Vapi Dashboard -> API Keys
    const publicKey = import.meta.env.VITE_VAPI_PUBLIC_KEY || '';
    // Fix for Vite / module resolution differences
    const VapiClass = Vapi.default || Vapi;
    vapiRef.current = new VapiClass(publicKey);

    const vapi = vapiRef.current;

    vapi.on('call-start', () => setCallStatus('active'));
    vapi.on('call-end', () => setCallStatus('inactive'));
    vapi.on('error', (e) => {
      console.error('Vapi Error:', e);
      setCallStatus('inactive');
      alert('Vapi voice error: ' + (e?.message || JSON.stringify(e)));
    });

    return () => {
      vapi.stop();
      vapi.removeAllListeners();
    };
  }, []);

  const toggleCall = async () => {
    const vapi = vapiRef.current;
    if (!vapi) return;

    if (callStatus === 'active') {
      vapi.stop();
      setCallStatus('inactive');
    } else {
      setCallStatus('loading');
      try {
        // Replace this ID or use env variable for your actual Assistant ID.
        const assistantId = import.meta.env.VITE_VAPI_ASSISTANT_ID || ''; 
        // Using a dummy assistant id as fallback, user needs to replace it if not valid
        await vapi.start(assistantId);
      } catch (err) {
        console.error(err);
        setCallStatus('inactive');
        alert('Failed to start Vapi call. Ensure Assistant ID is correct.');
      }
    }
  };

  return (
    <button
      onClick={toggleCall}
      className={`btn ${callStatus === 'active' ? 'btn-dark' : 'btn-primary'}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        boxShadow: callStatus === 'active' ? '0 0 15px rgba(201,100,66,0.4)' : 'none',
        transition: 'all 0.3s ease'
      }}
      disabled={callStatus === 'loading'}
    >
      {callStatus === 'inactive' && (
        <>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
          </svg>
          Call Helpline (Web)
        </>
      )}
      {callStatus === 'loading' && 'Connecting...'}
      {callStatus === 'active' && (
        <>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
          End Call
        </>
      )}
    </button>
  );
}
