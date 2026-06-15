import { useState, useEffect } from 'react';
import { ShieldCheck, Eye, EyeOff } from 'lucide-react';
import { API_BASE, apiFetch, logout as apiLogout, clearApiCache } from '../api/client';
import { useToast } from '../components/Toast';
import PlatformApp from './PlatformApp';

/* Standalone platform-operator login (separate from the club login). */
const PlatformLogin = ({ onLogin }) => {
  const { toast } = useToast();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    if (!username || !password) { setError('Введите логин и пароль'); return; }
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/accounts/login/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || 'Неверный логин или пароль'); return; }
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);

      // Verify platform-admin role
      const pr = await fetch(`${API_BASE}/api/v1/accounts/profile/`, {
        headers: { Authorization: `Bearer ${data.access}` },
      });
      const profile = pr.ok ? await pr.json() : {};
      if (profile?.user_type !== 'admin') {
        setError('Доступ только для администраторов платформы');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        return;
      }
      // Drop any leftover club-session keys so X-Club-Id of a previous club
      // is never sent with the platform-admin token.
      localStorage.removeItem('active_club_id');
      localStorage.removeItem('active_club_name');
      localStorage.removeItem('impersonate_mode');
      localStorage.setItem('username', profile.username || username);
      clearApiCache();
      onLogin();
    } catch {
      setError('Ошибка соединения с сервером');
    } finally { setLoading(false); }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'radial-gradient(circle at 50% 30%, #1a1635, #0d0d18)' }}>
      <form onSubmit={submit} style={{ width: 380, maxWidth: '90vw', background: 'var(--bg-panel)',
        border: '1px solid var(--border-color)', borderRadius: 18, padding: 36 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginBottom: 28 }}>
          <div style={{ width: 56, height: 56, borderRadius: 14, background: 'linear-gradient(135deg,#6366f1,#a855f7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ShieldCheck size={28} color="#fff" />
          </div>
          <div style={{ fontWeight: 800, fontSize: 20 }}>PCHub</div>
          <div style={{ fontSize: 11, color: '#f59e0b', fontWeight: 700, letterSpacing: 2 }}>PLATFORM CONTROL</div>
        </div>

        <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Логин</label>
        <input value={username} onChange={e => setUsername(e.target.value)} autoFocus
          style={{ width: '100%', boxSizing: 'border-box', height: 42, padding: '0 14px', marginBottom: 14,
            background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: 10,
            color: 'var(--text-main)', fontSize: 14, fontFamily: 'inherit' }} />

        <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Пароль</label>
        <div style={{ position: 'relative', marginBottom: 18 }}>
          <input type={show ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
            style={{ width: '100%', boxSizing: 'border-box', height: 42, padding: '0 40px 0 14px',
              background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: 10,
              color: 'var(--text-main)', fontSize: 14, fontFamily: 'inherit' }} />
          <button type="button" onClick={() => setShow(v => !v)}
            style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
              background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}>
            {show ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>

        {error && <div style={{ fontSize: 13, color: '#ef4444', marginBottom: 14, textAlign: 'center' }}>{error}</div>}

        <button type="submit" disabled={loading} className="btn btn-primary"
          style={{ width: '100%', height: 46, fontSize: 15, fontWeight: 600 }}>
          {loading ? 'Вход…' : 'Войти'}
        </button>

        <div style={{ marginTop: 16, textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
          Это панель оператора платформы.<br />
          Клубам — <a href="/" style={{ color: 'var(--accent)' }}>обычный вход</a>
        </div>
      </form>
    </div>
  );
};

const PlatformRoot = () => {
  const [authed, setAuthed] = useState(false);
  const [checking, setChecking] = useState(true);

  // On mount: if a token exists, verify it belongs to a platform admin
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) { setChecking(false); return; }
    apiFetch('/api/v1/accounts/profile/')
      .then(p => { if (p?.user_type === 'admin') setAuthed(true); })
      .catch(() => {})
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#0d0d18', color: 'var(--text-muted)' }}>Загрузка…</div>;
  }
  if (!authed) return <PlatformLogin onLogin={() => setAuthed(true)} />;
  return <PlatformApp />;
};

export default PlatformRoot;
