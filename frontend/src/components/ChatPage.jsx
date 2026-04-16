/**
 * VidyutSeva - Chat Page
 * Warm-dark theme (Claude-style #141413), streaming agent stage pills,
 * response text parsing to strip AgentScope JSON wrappers.
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = 'http://localhost:8000';

// ── Parse raw agent response into clean text ──────────────────────────────────
function parseAgentResponse(raw) {
  if (!raw) return '';
  let text = String(raw);

  // Strip AgentScope Msg wrapper: {'type': 'text', 'text': '...'}
  // or [{'type': 'text', 'text': '...'}]
  try {
    // Try JSON array format: [{"type":"text","text":"..."}]
    if (text.startsWith('[')) {
      const arr = JSON.parse(text.replace(/'/g, '"'));
      if (Array.isArray(arr)) {
        return arr.map(b => b.text || b.content || '').join('\n').trim();
      }
    }
    // Try single object: {"type":"text","text":"..."}
    if (text.startsWith('{')) {
      const obj = JSON.parse(text.replace(/'/g, '"'));
      if (obj.text) return obj.text.trim();
      if (obj.content) return obj.content.trim();
    }
  } catch (_) {}

  // Regex fallback: extract 'text': '...' value
  const match = text.match(/'text':\s*['"]([\s\S]*?)['"]\s*\}/);
  if (match) return match[1].replace(/\\n/g, '\n').trim();

  // Another fallback: "text": "..."
  const match2 = text.match(/"text":\s*"([\s\S]*?)"\s*\}/);
  if (match2) return match2[1].replace(/\\n/g, '\n').trim();

  // Clean up literal \n
  return text.replace(/\\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}

// ── Typing dots ───────────────────────────────────────────────────────────────
function TypingDots() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, marginLeft: 4 }}>
      {[0, 1, 2].map((i) => (
        <motion.span key={i}
          style={{ width: 4, height: 4, borderRadius: '50%', background: '#b0aea5', display: 'inline-block' }}
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.15, ease: 'easeInOut' }} />
      ))}
    </span>
  );
}

// ── Stage pill labels + colors ────────────────────────────────────────────────
const STAGE_META = {
  location:   { label: 'Location',   color: '#818cf8' },
  outage:     { label: 'Outage DB',  color: '#d97757' },
  diagnosis:  { label: 'Diagnosis',  color: '#34d399' },
  escalation: { label: 'Escalation', color: '#f87171' },
  complete:   { label: 'Complete',   color: '#a3e635' },
  error:      { label: 'Error',      color: '#b53333' },
};

function StagePill({ stage, status, message }) {
  const meta = STAGE_META[stage] || { label: stage, color: '#87867f' };
  return (
    <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
      style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px',
        borderRadius: 8, background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.06)',
        fontSize: 13, color: '#b0aea5', marginBottom: 4 }}>
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: meta.color,
        flexShrink: 0, boxShadow: status === 'thinking' ? `0 0 8px ${meta.color}` : 'none' }} />
      <span style={{ color: meta.color, fontWeight: 600, fontSize: 13 }}>{meta.label}</span>
      {status === 'thinking' ? <TypingDots /> : (
        <span style={{ opacity: 0.5, fontSize: 12, fontFamily: "'Inter', sans-serif" }}>{message}</span>
      )}
      {status === 'skipped' && <span style={{ opacity: 0.35, fontSize: 11, fontStyle: 'italic' }}>skipped</span>}
    </motion.div>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────────
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user';
  const cleanContent = isUser ? msg.content : parseAgentResponse(msg.content);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      style={{ display: 'flex', flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start', marginBottom: 24 }}>

      <div style={{ fontSize: 11, color: '#87867f', marginBottom: 4,
        paddingLeft: isUser ? 0 : 4, fontFamily: "'Inter', sans-serif" }}>
        {isUser ? 'You' : 'VidyutSeva AI'}
      </div>

      {/* Agent stage pills (AI messages only) */}
      {!isUser && msg.stages && msg.stages.length > 0 && (
        <div style={{ marginBottom: 10, width: '100%', maxWidth: 520 }}>
          {msg.stages.map((s, i) => <StagePill key={i} {...s} />)}
        </div>
      )}

      {/* Text bubble */}
      {cleanContent && (
        <div style={{
          maxWidth: '80%', padding: '14px 18px',
          borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
          background: isUser
            ? 'linear-gradient(135deg, #c96442, #d97757)'
            : 'rgba(255,255,255,0.06)',
          border: isUser ? 'none' : '1px solid rgba(255,255,255,0.06)',
          color: isUser ? '#faf9f5' : '#e8e6dc',
          fontSize: 15, lineHeight: 1.65,
          fontFamily: "'Georgia', serif",
          whiteSpace: 'pre-wrap',
        }}>
          {cleanContent}
        </div>
      )}

      {/* Meta badges */}
      {!isUser && msg.meta && (
        <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
          {msg.meta.outage_found && (
            <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 6,
              background: 'rgba(217,119,87,0.12)', color: '#d97757',
              border: '1px solid rgba(217,119,87,0.2)', fontWeight: 500 }}>
              Outage Found
            </span>
          )}
          {msg.meta.area && msg.meta.area !== 'unknown' && (
            <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 6,
              background: 'rgba(129,140,248,0.1)', color: '#818cf8',
              border: '1px solid rgba(129,140,248,0.15)', fontWeight: 500 }}>
              {msg.meta.area}
            </span>
          )}
          {msg.meta.diagnosis_type && (
            <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 6,
              background: 'rgba(52,211,153,0.1)', color: '#34d399',
              border: '1px solid rgba(52,211,153,0.15)', fontWeight: 500 }}>
              {msg.meta.diagnosis_type.replace('_', ' ')}
            </span>
          )}
          {msg.meta.escalation_triggered && (
            <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 6,
              background: 'rgba(248,113,113,0.1)', color: '#f87171',
              border: '1px solid rgba(248,113,113,0.15)', fontWeight: 500 }}>
              Escalated to Lineman
            </span>
          )}
        </div>
      )}
    </motion.div>
  );
}

// ── Quick suggestion prompts ──────────────────────────────────────────────────
const SUGGESTIONS = [
  "I'm in Koramangala, no power for 2 hours",
  "Transformer sparking near Indiranagar junction",
  "Is there a planned outage in Whitefield today?",
  "Power cable fallen on MG Road",
];

// ── Main Chat Component ───────────────────────────────────────────────────────
export default function ChatPage() {
  const [messages, setMessages] = useState([{
    id: 0, role: 'assistant',
    content: "Namaskara! I'm VidyutSeva's AI assistant. Tell me about your electricity issue in Bangalore and I'll check our live data, diagnose the problem, and escalate hardware faults automatically.",
    stages: [], meta: null,
  }]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const textareaRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = '52px';
    el.style.height = Math.min(el.scrollHeight, 180) + 'px';
  }, []);

  const sendMessage = useCallback(async (text) => {
    const msg = (text || input).trim();
    if (!msg || streaming) return;
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = '52px';

    const userMsgId = Date.now();
    const aiMsgId = userMsgId + 1;
    setMessages(prev => [...prev,
      { id: userMsgId, role: 'user', content: msg },
      { id: aiMsgId, role: 'assistant', content: '', stages: [], meta: null },
    ]);
    setStreaming(true);

    try {
      const url = new URL(`${API_BASE}/voice/chat/stream`);
      url.searchParams.set('message', msg);
      const es = new EventSource(url.toString());
      let finalResponse = '';
      let finalMeta = {};

      es.onmessage = (e) => {
        try {
          const evt = JSON.parse(e.data);
          const { stage, status, message: evtMsg, result } = evt;

          if (stage === 'complete') { es.close(); setStreaming(false); return; }
          if (stage === 'error') {
            setMessages(prev => prev.map(m => m.id === aiMsgId
              ? { ...m, content: `Error: ${evtMsg}`, stages: [...(m.stages||[]), { stage, status, message: evtMsg }] }
              : m));
            es.close(); setStreaming(false); return;
          }

          if (stage === 'diagnosis' && status === 'done' && result) {
            finalResponse = result.response || '';
            finalMeta = { outage_found: result.outage_found, area: result.area, diagnosis_type: result.diagnosis_type };
          }
          if (stage === 'escalation' && status === 'done') finalMeta.escalation_triggered = true;

          setMessages(prev => prev.map(m => {
            if (m.id !== aiMsgId) return m;
            const stages = [...(m.stages || [])];
            const idx = stages.findIndex(s => s.stage === stage);
            const pill = { stage, status, message: evtMsg };
            if (idx >= 0) stages[idx] = pill; else stages.push(pill);
            return { ...m, stages, content: finalResponse, meta: Object.keys(finalMeta).length > 0 ? finalMeta : m.meta };
          }));
        } catch (_) {}
      };

      es.onerror = () => {
        es.close(); setStreaming(false);
        setMessages(prev => prev.map(m =>
          m.id === aiMsgId && !m.content ? { ...m, content: 'Connection lost. Please try again.' } : m));
      };
    } catch (err) {
      setStreaming(false);
      setMessages(prev => prev.map(m =>
        m.id === aiMsgId ? { ...m, content: `Error: ${err.message}` } : m));
    }
  }, [input, streaming]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  return (
    <div style={{
      minHeight: '100vh', background: '#141413', display: 'flex', flexDirection: 'column',
      color: '#faf9f5', fontFamily: "'Inter', -apple-system, sans-serif",
      position: 'relative',
    }}>

      {/* Header bar */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 10,
        background: 'rgba(20,20,19,0.92)', backdropFilter: 'blur(16px)',
        borderBottom: '1px solid #30302e', padding: '12px 24px',
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: '#c96442',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 11, fontWeight: 800, color: '#faf9f5', letterSpacing: '-0.5px',
        }}>VS</div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#faf9f5' }}>VidyutSeva AI</div>
          <div style={{ fontSize: 11, color: '#87867f' }}>
            {streaming
              ? <span style={{ color: '#d97757' }}>Pipeline running<TypingDots /></span>
              : '4-agent pipeline \u2014 Bangalore electricity support'}
          </div>
        </div>
        <div style={{ marginLeft: 'auto' }}>
          <span style={{
            fontSize: 10, padding: '3px 8px', borderRadius: 6,
            background: 'rgba(52,211,153,0.08)', color: '#34d399',
            border: '1px solid rgba(52,211,153,0.15)',
            fontWeight: 600, letterSpacing: '0.5px',
          }}>LIVE</span>
        </div>
      </div>

      {/* Messages area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '32px 0' }}>
        <div style={{ maxWidth: 700, margin: '0 auto', padding: '0 24px' }}>

          {/* Welcome block */}
          {messages.length === 1 && (
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
              style={{ textAlign: 'center', marginBottom: 56 }}>
              <div style={{
                width: 56, height: 56, borderRadius: 14, margin: '0 auto 20px',
                background: '#c96442', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 18, fontWeight: 800, color: '#faf9f5', letterSpacing: '-0.5px',
                boxShadow: '0 8px 24px rgba(201,100,66,0.25)',
              }}>VS</div>
              <h1 style={{
                fontFamily: "'Georgia', serif", fontSize: 28, fontWeight: 500,
                color: '#faf9f5', marginBottom: 8, lineHeight: 1.2,
              }}>
                How can I help today?
              </h1>
              <p style={{ fontSize: 15, color: '#87867f', lineHeight: 1.6 }}>
                Report electricity issues &middot; Get instant diagnosis &middot; Hardware faults auto-escalated
              </p>
            </motion.div>
          )}

          {messages.map((msg) => <MessageBubble key={msg.id} msg={msg} />)}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Quick suggestions */}
      <AnimatePresence>
        {messages.length === 1 && !streaming && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }} style={{ paddingBottom: 12 }}>
            <div style={{ maxWidth: 700, margin: '0 auto', padding: '0 24px',
              display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
              {SUGGESTIONS.map((s, i) => (
                <motion.button key={i} onClick={() => sendMessage(s)}
                  initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
                  style={{
                    padding: '8px 14px', borderRadius: 8,
                    background: '#30302e', border: '1px solid #30302e',
                    color: '#b0aea5', fontSize: 13, cursor: 'pointer',
                    fontFamily: "'Inter', sans-serif",
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => { e.target.style.background = '#3d3d3a'; e.target.style.color = '#faf9f5'; }}
                  onMouseLeave={(e) => { e.target.style.background = '#30302e'; e.target.style.color = '#b0aea5'; }}>
                  {s}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input area */}
      <div style={{ maxWidth: 700, margin: '0 auto', width: '100%', padding: '0 24px 24px' }}>
        <div style={{
          background: '#1e1e1c',
          border: `1px solid ${inputFocused ? '#4d4c48' : '#30302e'}`,
          borderRadius: 16, overflow: 'hidden',
          boxShadow: inputFocused
            ? '#30302e 0px 0px 0px 0px, #4d4c48 0px 0px 0px 1px'
            : '#1e1e1c 0px 0px 0px 0px, #30302e 0px 0px 0px 1px',
          transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
        }}>
          <div style={{ padding: '14px 16px 6px' }}>
            <textarea
              ref={textareaRef} value={input}
              onChange={(e) => { setInput(e.target.value); adjustHeight(); }}
              onKeyDown={handleKeyDown}
              onFocus={() => setInputFocused(true)}
              onBlur={() => setInputFocused(false)}
              placeholder="Describe your electricity issue..."
              disabled={streaming}
              style={{
                width: '100%', background: 'transparent', border: 'none', outline: 'none',
                color: '#faf9f5', fontSize: 15, lineHeight: 1.6,
                resize: 'none', fontFamily: "'Inter', sans-serif",
                minHeight: 52, maxHeight: 180,
              }} />
          </div>
          <div style={{ padding: '6px 16px 14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: '#5e5d59' }}>
              {streaming ? 'Agent pipeline running...' : 'Press Enter to send, Shift+Enter for new line'}
            </span>
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || streaming}
              style={{
                padding: '8px 20px', borderRadius: 12, border: 'none', cursor: 'pointer',
                fontSize: 14, fontWeight: 600, fontFamily: "'Inter', sans-serif",
                background: input.trim() && !streaming ? '#c96442' : '#30302e',
                color: input.trim() && !streaming ? '#faf9f5' : '#5e5d59',
                transition: 'all 0.2s',
                boxShadow: input.trim() && !streaming
                  ? '#c96442 0px 0px 0px 0px, #c96442 0px 0px 0px 1px'
                  : 'none',
              }}>
              {streaming ? 'Processing...' : 'Send'}
            </button>
          </div>
        </div>
      </div>

      <style>{`
        textarea::placeholder { color: #5e5d59 !important; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #30302e; border-radius: 2px; }
      `}</style>
    </div>
  );
}
