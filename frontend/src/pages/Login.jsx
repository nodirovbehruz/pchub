import React, { useState } from 'react';
import {
  Phone, Lock, ShieldCheck, Gamepad2, Search,
  Building2, DollarSign, ChevronRight, Mail,
  User, UserPlus, ArrowLeft, CheckCircle2,
} from 'lucide-react';

const EyeIcon = ({ open }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
       stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {open ? (
      <>
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ) : (
      <>
        <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a19.79 19.79 0 0 1 5.06-5.94" />
        <path d="M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a19.79 19.79 0 0 1-2.16 3.19" />
        <path d="M14.12 14.12a3 3 0 1 1-4.24-4.24" />
        <line x1="1" y1="1" x2="23" y2="23" />
      </>
    )}
  </svg>
);

import './Login.css';

const API_BASE = '';

/* ── helpers ── */
function formatPhone(raw) {
  // strip everything except digits and leading +
  let v = raw.replace(/[^\d+]/g, '');
  // normalize: if starts with 8 → +7
  if (v.startsWith('8') && v.length > 1) v = '+7' + v.slice(1);
  // add + if starts with 7 and no +
  if (v.startsWith('7') && !v.startsWith('+')) v = '+' + v;
  return v;
}

/* ══════════════════════════════════════════════════════
   Login (existing 3-step flow)
══════════════════════════════════════════════════════ */
const LoginFlow = ({ onLogin, onSwitchToRegister }) => {
  const [step, setStep] = useState(1);
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [clubs, setClubs] = useState([]);
  const [clubsLoading, setClubsLoading] = useState(false);
  const [clubSearch, setClubSearch] = useState('');
  const [selectedClub, setSelectedClub] = useState(null);

  const [cashAmount, setCashAmount] = useState('0');
  const [openingShift, setOpeningShift] = useState(false);

  // Create-club inline form
  const [showCreateClub, setShowCreateClub] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newClub, setNewClub] = useState({ name: '', city: '', street: '', contact_phone: '' });

  const loadClubs = async (accessToken) => {
    setClubsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/clubs/my/`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      const data = await res.json();
      if (!res.ok) { setError('Не удалось загрузить клубы'); return; }
      const list = Array.isArray(data) ? data : (Array.isArray(data.results) ? data.results : []);
      setClubs(list.map(c => ({
        id: c.id, name: c.name, address: c.address,
        hasShift: c.has_shift, isTrial: c.is_trial,
      })));
    } catch { setError('Не удалось загрузить клубы'); }
    finally { setClubsLoading(false); }
  };

  const handlePhoneLogin = async (e) => {
    e.preventDefault();
    if (!phone || !password) { setError('Введите телефон и пароль'); return; }
    setLoading(true); setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/accounts/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: phone, password }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || 'Неверный телефон или пароль'); return; }
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      // BUGFIX: the backend issues tokens WITHOUT custom role/username claims, so
      // reading payload.role/username always yielded undefined → everyone became
      // 'operator'. Username comes from the entered login; the real per-club role is
      // set from the chosen club's membership below.
      localStorage.setItem('username', phone);

      // Determine account type — platform admins skip club selection entirely.
      let userType = 'user';
      try {
        const pr = await fetch(`${API_BASE}/api/v1/accounts/profile/`, {
          headers: { Authorization: `Bearer ${data.access}` },
        });
        if (pr.ok) userType = (await pr.json())?.user_type || 'user';
      } catch {}

      if (userType === 'admin') {
        // Platform operator → dedicated /platform panel. Hard-navigate so the
        // club UI never flashes, and clear any leftover club/impersonate keys.
        localStorage.removeItem('active_club_id');
        localStorage.removeItem('active_club_name');
        localStorage.removeItem('impersonate_mode');
        window.location.href = '/platform';
        return;
      }
      // Regular club user: ensure no stale impersonate flag remains.
      localStorage.removeItem('impersonate_mode');

      await loadClubs(data.access);
      // Auto-select when there is exactly one club — no need to ask.
      // (clubs state may not be set yet; re-fetch the list here)
      const res2 = await fetch(`${API_BASE}/api/v1/clubs/my/`, {
        headers: { Authorization: `Bearer ${data.access}` },
      });
      const cd = await res2.json().catch(() => []);
      const list = Array.isArray(cd) ? cd : (Array.isArray(cd.results) ? cd.results : []);
      if (list.length === 1) {
        const only = list[0];
        setSelectedClub({ id: only.id, name: only.name, address: only.address, hasShift: only.has_shift, isTrial: only.is_trial, role: only.role });
        localStorage.setItem('active_club_id', String(only.id));
        localStorage.setItem('active_club_name', only.name);
        localStorage.setItem('active_club_role', only.role || 'operator');
        setStep(3);  // jump straight to shift step
      } else {
        setStep(2);  // multiple clubs → let the user choose
      }
    } catch { setError('Ошибка соединения с сервером'); }
    finally { setLoading(false); }
  };

  const handleSelectClub = () => {
    if (!selectedClub) { setError('Выберите клуб'); return; }
    setError('');
    localStorage.setItem('active_club_id', String(selectedClub.id));
    localStorage.setItem('active_club_name', selectedClub.name);
    localStorage.setItem('active_club_role', selectedClub.role || 'operator');
    setStep(3);
  };

  const handleOpenShift = async () => {
    setError(''); setOpeningShift(true);
    try {
      const token = localStorage.getItem('access_token');
      const clubId = localStorage.getItem('active_club_id');
      const res = await fetch(`${API_BASE}/api/v1/billing/shifts/open/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
          ...(clubId ? { 'X-Club-Id': clubId } : {}),
        },
        body: JSON.stringify({ initial_cash: parseFloat(cashAmount) || 0 }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data ? Object.values(data).flat().join(', ') : 'Ошибка открытия смены');
        return;
      }
      onLogin({ username: localStorage.getItem('username') || phone, role: localStorage.getItem('active_club_role') || 'operator', clubName: selectedClub?.name || '' });
    } catch (e) { setError('Ошибка: ' + e.message); }
    finally { setOpeningShift(false); }
  };

  const handleCreateClub = async (e) => {
    e.preventDefault();
    if (!newClub.name.trim()) return;
    setCreating(true); setError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${API_BASE}/api/v1/clubs/my/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: newClub.name.trim(),
          city: newClub.city.trim(),
          street: newClub.street.trim(),
          contact_phone: newClub.contact_phone.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(Object.values(data).flat().join(', ') || 'Ошибка создания клуба');
        return;
      }
      // Add to list and auto-select
      const created = { id: data.id, name: data.name, address: data.address || '', hasShift: false, isTrial: data.is_trial };
      setClubs(prev => [...prev, created]);
      setSelectedClub(created);
      setShowCreateClub(false);
      setNewClub({ name: '', city: '', street: '', contact_phone: '' });
    } catch { setError('Ошибка соединения'); }
    finally { setCreating(false); }
  };

  const filteredClubs = clubs.filter(c =>
    c.name.toLowerCase().includes(clubSearch.toLowerCase()) ||
    (c.address || '').toLowerCase().includes(clubSearch.toLowerCase())
  );

  return (
    <>
      {/* Step 1 — Login */}
      {step === 1 && (
        <div className="login-card">
          <div className="login-header">
            <div className="logo-container"><Gamepad2 size={32} className="brand-logo" /></div>
            <h2>Вход в панель управления</h2>
          </div>

          {error && <div className="login-error"><ShieldCheck size={18} />{error}</div>}

          <form onSubmit={handlePhoneLogin} className="login-form">
            <div className="input-group">
              <label>Телефон / Логин</label>
              <div className="input-with-icon">
                <Phone size={18} className="input-icon" />
                <input type="text" placeholder="+71234567890 или admin"
                  value={phone} onChange={e => setPhone(e.target.value)} autoFocus required />
              </div>
            </div>
            <div className="input-group">
              <label>Пароль</label>
              <div className="input-with-icon">
                <Lock size={18} className="input-icon" />
                <input type={showPassword ? 'text' : 'password'} placeholder="••••••••"
                  value={password} onChange={e => setPassword(e.target.value)} required />
                <button type="button" className="password-toggle"
                  onClick={() => setShowPassword(v => !v)} tabIndex={-1}>
                  <EyeIcon open={!showPassword} />
                </button>
              </div>
            </div>
            <button type="submit" className="login-button" disabled={loading}>
              {loading ? <div className="spinner"></div> : 'Войти'}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Нет аккаунта? </span>
            <button className="link-button" onClick={onSwitchToRegister} style={{ fontSize: '13px' }}>
              Зарегистрироваться
            </button>
          </div>
        </div>
      )}

      {/* Step 2 — Select club */}
      {step === 2 && (
        <div className="login-card club-card-wrapper">
          <div className="login-header"><h2>Выберите клуб</h2></div>
          {error && <div className="login-error"><ShieldCheck size={18} />{error}</div>}

          {/* Create-club inline form */}
          {showCreateClub ? (
            <form onSubmit={handleCreateClub} className="login-form">
              <div className="input-group">
                <label>Название клуба <span style={{ color: '#ef4444' }}>*</span></label>
                <div className="input-with-icon">
                  <Building2 size={18} className="input-icon" />
                  <input type="text" placeholder="GameZone, CyberArena…"
                    value={newClub.name} autoFocus required
                    onChange={e => setNewClub(f => ({ ...f, name: e.target.value }))} />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="input-group">
                  <label>Город</label>
                  <input type="text" placeholder="Москва"
                    value={newClub.city}
                    onChange={e => setNewClub(f => ({ ...f, city: e.target.value }))}
                    style={{ background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: 8, padding: '10px 12px', color: 'white', fontSize: 14, fontFamily: 'inherit', width: '100%' }} />
                </div>
                <div className="input-group">
                  <label>Телефон</label>
                  <input type="tel" placeholder="+7..."
                    value={newClub.contact_phone}
                    onChange={e => setNewClub(f => ({ ...f, contact_phone: e.target.value }))}
                    style={{ background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: 8, padding: '10px 12px', color: 'white', fontSize: 14, fontFamily: 'inherit', width: '100%' }} />
                </div>
              </div>
              <div className="input-group">
                <label>Адрес</label>
                <input type="text" placeholder="ул. Ленина, 42"
                  value={newClub.street}
                  onChange={e => setNewClub(f => ({ ...f, street: e.target.value }))}
                  style={{ background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: 8, padding: '10px 12px', color: 'white', fontSize: 14, fontFamily: 'inherit', width: '100%' }} />
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <button type="button" className="login-button"
                  onClick={() => { setShowCreateClub(false); setError(''); }}
                  style={{ background: 'var(--hover-overlay)', color: 'var(--text-muted)', boxShadow: 'none', flex: 1 }}>
                  Отмена
                </button>
                <button type="submit" className="login-button" disabled={creating || !newClub.name.trim()} style={{ flex: 2 }}>
                  {creating ? <div className="spinner"></div> : <><Building2 size={16} /> Создать клуб</>}
                </button>
              </div>
            </form>
          ) : (
            <>
              {clubs.length > 0 && (
                <div className="input-with-icon" style={{ marginBottom: '16px' }}>
                  <Search size={18} className="input-icon" />
                  <input type="text" placeholder="Быстрый поиск клуба"
                    value={clubSearch} onChange={e => setClubSearch(e.target.value)} autoFocus />
                </div>
              )}
              <div className="club-list">
                {clubsLoading && <div className="club-empty">Загрузка клубов…</div>}
                {!clubsLoading && clubs.length === 0 && (
                  <div style={{ textAlign: 'center', padding: '32px 16px' }}>
                    <Building2 size={40} style={{ opacity: 0.2, marginBottom: 12 }} />
                    <div style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 6 }}>У вас пока нет клубов</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Создайте первый клуб, чтобы начать работу</div>
                  </div>
                )}
                {!clubsLoading && clubs.length > 0 && filteredClubs.length === 0 && (
                  <div className="club-empty">Клубы не найдены</div>
                )}
                {filteredClubs.map(club => (
                  <div key={club.id}
                    className={`club-row ${selectedClub?.id === club.id ? 'selected' : ''}`}
                    onClick={() => setSelectedClub(club)}>
                    <div className="club-row-main">
                      <div className="club-row-name">{club.name}</div>
                      <div className="club-row-address">{club.address}</div>
                      <div className="club-row-badges">
                        <span className="club-badge muted">{club.hasShift ? 'Смена открыта' : 'Нет смены'}</span>
                        {club.isTrial && <span className="club-badge trial">Trial</span>}
                      </div>
                    </div>
                    <Building2 size={20} style={{ opacity: 0.4 }} />
                  </div>
                ))}
              </div>

              {/* Add club button — always visible */}
              <button type="button"
                onClick={() => { setShowCreateClub(true); setError(''); }}
                style={{
                  marginTop: 14, width: '100%', padding: '10px',
                  background: 'transparent', border: '1px dashed var(--border-color)',
                  borderRadius: 10, color: 'var(--accent-blue)',
                  fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  transition: 'border-color 0.2s, background 0.2s',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent-blue)'; e.currentTarget.style.background = 'rgba(99,102,241,0.06)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-color)'; e.currentTarget.style.background = 'transparent'; }}>
                <Building2 size={15} /> + Добавить клуб
              </button>

              <button className="login-button" onClick={handleSelectClub}
                disabled={!selectedClub} style={{ marginTop: 12 }}>
                Выбрать клуб <ChevronRight size={18} />
              </button>
            </>
          )}
        </div>
      )}

      {/* Step 3 — Open shift */}
      {step === 3 && (
        <div className="login-card">
          <div className="login-header"><h2>Открытие новой смены</h2></div>
          {error && <div className="login-error"><ShieldCheck size={18} />{error}</div>}
          <div className="input-group">
            <label>Наличных в кассе</label>
            <div className="input-with-icon">
              <DollarSign size={18} className="input-icon" />
              <input type="number" value={cashAmount}
                onChange={e => setCashAmount(e.target.value)} min="0" step="0.01" autoFocus />
            </div>
          </div>
          <div className="selected-club-block">
            <Building2 size={18} style={{ opacity: 0.5, marginRight: '10px' }} />
            <div>
              <div className="club-row-name" style={{ fontSize: '14px' }}>{selectedClub?.name}</div>
              <div className="club-row-address">{selectedClub?.address}</div>
            </div>
          </div>
          <button className="login-button" onClick={handleOpenShift} disabled={openingShift} style={{ marginTop: '20px' }}>
            {openingShift ? <div className="spinner"></div> : 'Открыть смену'}
          </button>
          <div className="step-links">
            <button type="button" className="link-button"
              onClick={() => onLogin({ username: localStorage.getItem('username'), role: localStorage.getItem('active_club_role') || 'operator', clubName: selectedClub?.name || '' })}>
              Продолжить без смены
            </button>
            <button type="button" className="link-button" onClick={() => setStep(2)}>
              Выбрать другой клуб
            </button>
          </div>
        </div>
      )}
    </>
  );
};

/* ══════════════════════════════════════════════════════
   Registration (new — 2-step: form → success)
══════════════════════════════════════════════════════ */
const RegisterFlow = ({ onSwitchToLogin }) => {
  const [regStep, setRegStep] = useState(1); // 1=form, 2=success
  const [form, setForm] = useState({
    firstName: '', lastName: '', phone: '', email: '',
    password: '', passwordConfirm: '', agreed: false,
  });
  const [showPass, setShowPass] = useState(false);
  const [showPass2, setShowPass2] = useState(false);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState('');

  const set = (field) => (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm(f => ({ ...f, [field]: val }));
    setErrors(prev => ({ ...prev, [field]: '' }));
  };

  const validate = () => {
    const e = {};
    if (!form.firstName.trim()) e.firstName = 'Введите имя';
    if (!form.phone.trim()) e.phone = 'Введите номер телефона';
    else if (!/^\+\d{10,15}$/.test(formatPhone(form.phone)))
      e.phone = 'Формат: +7XXXXXXXXXX';
    if (form.email && !/\S+@\S+\.\S+/.test(form.email)) e.email = 'Некорректный email';
    if (!form.password) e.password = 'Введите пароль';
    else if (form.password.length < 8) e.password = 'Минимум 8 символов';
    if (form.password !== form.passwordConfirm) e.passwordConfirm = 'Пароли не совпадают';
    if (!form.agreed) e.agreed = 'Необходимо принять условия';
    return e;
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }

    const normalPhone = formatPhone(form.phone);
    setLoading(true); setServerError('');

    try {
      const res = await fetch(`${API_BASE}/api/v1/accounts/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: normalPhone,   // phone is the login
          phone: normalPhone,
          email: form.email || undefined,
          first_name: form.firstName,
          last_name: form.lastName,
          password: form.password,
          password_confirm: form.passwordConfirm,
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        // Parse DRF field errors
        const fieldMap = {
          username: 'phone', phone: 'phone', email: 'email',
          password: 'password', password_confirm: 'passwordConfirm',
          first_name: 'firstName', last_name: 'lastName',
        };
        const fieldErrors = {};
        let generalError = '';
        for (const [key, msgs] of Object.entries(data)) {
          const msg = Array.isArray(msgs) ? msgs[0] : msgs;
          if (fieldMap[key]) fieldErrors[fieldMap[key]] = msg;
          else generalError += msg + ' ';
        }
        if (Object.keys(fieldErrors).length > 0) setErrors(fieldErrors);
        else setServerError(generalError || 'Ошибка регистрации');
        return;
      }

      setRegStep(2); // → success screen
    } catch {
      setServerError('Ошибка соединения с сервером');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: success
  if (regStep === 2) {
    return (
      <div className="login-card" style={{ textAlign: 'center' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', padding: '24px 0' }}>
          <div style={{
            width: 72, height: 72, borderRadius: '50%',
            background: 'rgba(16,185,129,0.15)', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
          }}>
            <CheckCircle2 size={40} color="#10b981" />
          </div>
          <h2 style={{ margin: 0, fontSize: '22px', color: 'white' }}>Регистрация завершена!</h2>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '14px', lineHeight: 1.6, maxWidth: 300 }}>
            Аккаунт успешно создан. Теперь вы можете войти в панель управления.
          </p>
          <button className="login-button" onClick={onSwitchToLogin} style={{ marginTop: '8px', maxWidth: 280 }}>
            Войти в систему
          </button>
        </div>
      </div>
    );
  }

  // Step 1: registration form
  return (
    <div className="login-card" style={{ maxWidth: 460 }}>
      <div className="login-header">
        <div className="logo-container">
          <UserPlus size={30} className="brand-logo" />
        </div>
        <h2>Регистрация</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Создайте аккаунт для управления клубом</p>
      </div>

      {serverError && <div className="login-error"><ShieldCheck size={18} />{serverError}</div>}

      <form onSubmit={handleRegister} className="login-form">
        {/* Name row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div className="input-group">
            <label>Имя <span style={{ color: '#ef4444' }}>*</span></label>
            <div className="input-with-icon">
              <User size={16} className="input-icon" />
              <input type="text" placeholder="Иван"
                value={form.firstName} onChange={set('firstName')}
                style={{ borderColor: errors.firstName ? '#ef4444' : '' }} />
            </div>
            {errors.firstName && <span className="field-error">{errors.firstName}</span>}
          </div>
          <div className="input-group">
            <label>Фамилия</label>
            <div className="input-with-icon">
              <User size={16} className="input-icon" />
              <input type="text" placeholder="Иванов"
                value={form.lastName} onChange={set('lastName')} />
            </div>
          </div>
        </div>

        {/* Phone */}
        <div className="input-group">
          <label>Телефон <span style={{ color: '#ef4444' }}>*</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 400, marginLeft: 6 }}>
              (будет логином)
            </span>
          </label>
          <div className="input-with-icon">
            <Phone size={18} className="input-icon" />
            <input type="tel" placeholder="+79123456789"
              value={form.phone}
              onChange={e => {
                setForm(f => ({ ...f, phone: e.target.value }));
                setErrors(prev => ({ ...prev, phone: '' }));
              }}
              onBlur={e => setForm(f => ({ ...f, phone: formatPhone(e.target.value) }))}
              style={{ borderColor: errors.phone ? '#ef4444' : '' }} />
          </div>
          {errors.phone && <span className="field-error">{errors.phone}</span>}
        </div>

        {/* Email */}
        <div className="input-group">
          <label>Email
            <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 400, marginLeft: 6 }}>
              (для уведомлений)
            </span>
          </label>
          <div className="input-with-icon">
            <Mail size={18} className="input-icon" />
            <input type="email" placeholder="ivanov@example.com"
              value={form.email} onChange={set('email')}
              style={{ borderColor: errors.email ? '#ef4444' : '' }} />
          </div>
          {errors.email && <span className="field-error">{errors.email}</span>}
        </div>

        {/* Password */}
        <div className="input-group">
          <label>Пароль <span style={{ color: '#ef4444' }}>*</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 400, marginLeft: 6 }}>
              (минимум 8 символов)
            </span>
          </label>
          <div className="input-with-icon">
            <Lock size={18} className="input-icon" />
            <input type={showPass ? 'text' : 'password'} placeholder="••••••••"
              value={form.password} onChange={set('password')}
              style={{ borderColor: errors.password ? '#ef4444' : '' }} />
            <button type="button" className="password-toggle"
              onClick={() => setShowPass(v => !v)} tabIndex={-1}>
              <EyeIcon open={!showPass} />
            </button>
          </div>
          {errors.password && <span className="field-error">{errors.password}</span>}
        </div>

        {/* Confirm password */}
        <div className="input-group">
          <label>Подтвердите пароль <span style={{ color: '#ef4444' }}>*</span></label>
          <div className="input-with-icon">
            <Lock size={18} className="input-icon" />
            <input type={showPass2 ? 'text' : 'password'} placeholder="••••••••"
              value={form.passwordConfirm} onChange={set('passwordConfirm')}
              style={{ borderColor: errors.passwordConfirm ? '#ef4444' : '' }} />
            <button type="button" className="password-toggle"
              onClick={() => setShowPass2(v => !v)} tabIndex={-1}>
              <EyeIcon open={!showPass2} />
            </button>
          </div>
          {errors.passwordConfirm && <span className="field-error">{errors.passwordConfirm}</span>}
        </div>

        {/* Password strength indicator */}
        {form.password && (
          <PasswordStrength password={form.password} />
        )}

        {/* Terms */}
        <label className="terms-checkbox">
          <input type="checkbox" checked={form.agreed}
            onChange={e => { setForm(f => ({ ...f, agreed: e.target.checked })); setErrors(p => ({ ...p, agreed: '' })); }} />
          <span>
            Принимаю <a href="#" style={{ color: 'var(--accent-blue)' }}>Пользовательское соглашение</a> и{' '}
            <a href="#" style={{ color: 'var(--accent-blue)' }}>Политику обработки персональных данных</a>
          </span>
        </label>
        {errors.agreed && <span className="field-error">{errors.agreed}</span>}

        <button type="submit" className="login-button" disabled={loading || !form.agreed}>
          {loading ? <div className="spinner"></div> : <><UserPlus size={18} /> Зарегистрироваться</>}
        </button>
      </form>

      <div style={{ textAlign: 'center', marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
        <button className="link-button" onClick={onSwitchToLogin}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}>
          <ArrowLeft size={14} /> Уже есть аккаунт? Войти
        </button>
      </div>
    </div>
  );
};

/* ── Password strength bar ── */
const PasswordStrength = ({ password }) => {
  const score = (() => {
    let s = 0;
    if (password.length >= 8) s++;
    if (password.length >= 12) s++;
    if (/[A-Z]/.test(password)) s++;
    if (/[0-9]/.test(password)) s++;
    if (/[^A-Za-z0-9]/.test(password)) s++;
    return s;
  })();
  const levels = [
    { label: 'Слабый',      color: '#ef4444' },
    { label: 'Слабый',      color: '#ef4444' },
    { label: 'Средний',     color: '#f59e0b' },
    { label: 'Хороший',     color: '#10b981' },
    { label: 'Отличный',    color: '#10b981' },
    { label: 'Отличный',    color: '#10b981' },
  ];
  const { label, color } = levels[score] || levels[0];
  return (
    <div style={{ marginTop: -8 }}>
      <div style={{ display: 'flex', gap: '4px', marginBottom: '4px' }}>
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} style={{
            flex: 1, height: 3, borderRadius: 2,
            background: i <= score ? color : 'var(--border-color)',
            transition: 'background 0.2s',
          }} />
        ))}
      </div>
      <span style={{ fontSize: '11px', color }}>{label}</span>
    </div>
  );
};

/* ══════════════════════════════════════════════════════
   Root component — toggles between login / register
══════════════════════════════════════════════════════ */
const Login = ({ onLogin }) => {
  const [mode, setMode] = useState('login'); // 'login' | 'register'

  return (
    <div className="login-container">
      <div className="login-wizard">
        {mode === 'login'
          ? <LoginFlow onLogin={onLogin} onSwitchToRegister={() => setMode('register')} />
          : <RegisterFlow onSwitchToLogin={() => setMode('login')} />
        }
        <div className="login-footer-global">
          <p>PCHub Engine · v3.3.5</p>
        </div>
      </div>
    </div>
  );
};

export default Login;
