import { useEffect, useState, useCallback, createContext, useContext } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

const ToastContext = createContext({ toast: () => {} });

const TYPE_META = {
  success: { color: '#10b981', bg: 'rgba(16,185,129,0.12)', border: 'rgba(16,185,129,0.4)', icon: CheckCircle },
  error:   { color: '#ef4444', bg: 'rgba(239,68,68,0.12)',  border: 'rgba(239,68,68,0.4)',  icon: XCircle },
  warning: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.4)', icon: AlertTriangle },
  info:    { color: '#3b82f6', bg: 'rgba(59,130,246,0.12)', border: 'rgba(59,130,246,0.4)', icon: Info },
};

let nextId = 1;

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const remove = useCallback((id) => {
    setToasts(t => t.filter(x => x.id !== id));
  }, []);

  const toast = useCallback((message, options = {}) => {
    const id = nextId++;
    const type = options.type || 'info';
    const duration = options.duration ?? 4000;
    setToasts(t => [...t, { id, message, type }]);
    if (duration > 0) setTimeout(() => remove(id), duration);
  }, [remove]);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div style={{
        position: 'fixed', top: '20px', right: '20px', zIndex: 9999,
        display: 'flex', flexDirection: 'column', gap: '8px',
        maxWidth: '380px', pointerEvents: 'none',
      }}>
        {toasts.map(t => {
          const m = TYPE_META[t.type] || TYPE_META.info;
          const Icon = m.icon;
          return (
            <div key={t.id} style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '12px 16px',
              background: m.bg,
              border: `1px solid ${m.border}`,
              borderRadius: '10px',
              backdropFilter: 'blur(8px)',
              boxShadow: '0 8px 20px rgba(0,0,0,0.3)',
              animation: 'toast-slide 0.25s ease-out',
              pointerEvents: 'auto',
            }}>
              <Icon size={18} color={m.color} />
              <div style={{ flex: 1, fontSize: '13px', color: 'var(--text-light, white)' }}>{t.message}</div>
              <button onClick={() => remove(t.id)}
                style={{ background: 'transparent', border: 'none', color: m.color, cursor: 'pointer', padding: 0, display: 'flex' }}>
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
      <style>{`
        @keyframes toast-slide {
          from { opacity: 0; transform: translateX(20px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </ToastContext.Provider>
  );
};

export const useToast = () => useContext(ToastContext);

// Standalone helper for use outside React tree (e.g. apiFetch). Sets up
// a global function once provider is mounted.
let globalToast = (msg, opts) => console.warn('[toast]', msg, opts);
export const setGlobalToast = (fn) => { globalToast = fn; };
export const showToast = (msg, opts) => globalToast(msg, opts);
