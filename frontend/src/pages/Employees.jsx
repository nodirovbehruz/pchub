import { useState, useEffect, useCallback } from 'react';
import {
  Search, Plus, X, RefreshCw, User,
  Eye, EyeOff, ChevronRight,
  Crown, Shield, UserCheck, UserCog,
  Calculator, Megaphone, Users,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

/* ──────────────────── ROLES CONFIG ──────────────────── */
const ALL_ROLES = [
  {
    value: 'owner',
    label: 'Владелец',
    icon: Crown,
    color: '#f59e0b',
    bg: 'rgba(245,158,11,0.12)',
    perms: [
      'Полный доступ ко всем функциям',
      'Управление сотрудниками и ролями',
      'Настройка клуба и тарифов',
      'Финансовые отчёты и аналитика',
      'Управление акциями и бонусами',
    ],
  },
  {
    value: 'manager',
    label: 'Менеджер',
    icon: UserCog,
    color: '#6366f1',
    bg: 'rgba(99,102,241,0.12)',
    perms: [
      'Управление сеансами и бронированиями',
      'Работа с кассой и сменами',
      'Продажа тарифов, товаров и услуг',
      'Редактирование профилей клиентов',
      'Просмотр аналитики смены',
    ],
  },
  {
    value: 'operator',
    label: 'Оператор',
    icon: UserCheck,
    color: '#10b981',
    bg: 'rgba(16,185,129,0.12)',
    perms: [
      'Открытие и закрытие смены',
      'Продажа тарифов и товаров',
      'Управление картой клуба',
      'Регистрация и поиск клиентов',
    ],
  },
  {
    value: 'admin',
    label: 'Сис. администратор',
    icon: Shield,
    color: '#ef4444',
    bg: 'rgba(239,68,68,0.12)',
    perms: [
      'Полный API-доступ',
      'Системные настройки и интеграции',
      'Управление пользователями',
      'Просмотр логов и журналов',
    ],
    // SECURITY: platform super-admin — NOT assignable from club staff management
    // (would bypass club isolation for all clubs). Display-only for existing admins.
    readOnly: true,
  },
  {
    value: 'accountant',
    label: 'Бухгалтер',
    icon: Calculator,
    color: '#8b5cf6',
    bg: 'rgba(139,92,246,0.12)',
    perms: [
      'Просмотр финансовых отчётов',
      'Экспорт данных по сменам',
      'Аналитика по платежам',
      'Только чтение — без изменений',
    ],
    readOnly: true,  // display-only role, maps to manager on backend
  },
  {
    value: 'marketer',
    label: 'Маркетолог',
    icon: Megaphone,
    color: '#ec4899',
    bg: 'rgba(236,72,153,0.12)',
    perms: [
      'Управление акциями и промокодами',
      'Редактирование новостей и контента',
      'Настройка программы лояльности',
      'Просмотр клиентской базы',
    ],
    readOnly: true,  // display-only role, maps to manager on backend
  },
  {
    value: 'user',
    label: 'Другой сотрудник',
    icon: Users,
    color: '#64748b',
    bg: 'rgba(100,116,139,0.12)',
    perms: [
      'Ограниченный доступ',
      'Назначается индивидуально',
    ],
    readOnly: true,  // display-only, maps to operator on backend
  },
];

// Only the roles that the backend actually supports for assignment
const ASSIGN_ROLES = ALL_ROLES.filter(r => !r.readOnly);

const getRoleConf = (val) =>
  ALL_ROLES.find(r => r.value === val) || ALL_ROLES.find(r => r.value === 'operator');

/* ──────────────────── HELPERS ──────────────────── */
const iStyle = {
  width: '100%', boxSizing: 'border-box', height: 38,
  padding: '0 12px',
  background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
  borderRadius: 8, color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit',
  outline: 'none',
};

const Avatar = ({ name, size = 36, color, bg }) => {
  const initials = (name || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: bg || 'rgba(99,102,241,0.15)',
      border: `1.5px solid ${color || 'rgba(99,102,241,0.3)'}40`,
      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      fontSize: size * 0.35, fontWeight: 700,
      color: color || '#6366f1',
    }}>
      {initials}
    </div>
  );
};

const RoleBadge = ({ role }) => {
  const rc = getRoleConf(role);
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 10px', borderRadius: 20,
      background: rc.bg, color: rc.color,
      fontSize: '12px', fontWeight: 600, whiteSpace: 'nowrap',
    }}>
      <rc.icon size={11} />
      {rc.label}
    </span>
  );
};

const StatusBadges = ({ isActive = true }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontSize: '12px', fontWeight: 500,
      color: isActive ? '#10b981' : '#ef4444',
    }}>
      <span style={{
        width: 7, height: 7, borderRadius: '50%',
        background: isActive ? '#10b981' : '#ef4444', flexShrink: 0,
      }} />
      {isActive ? 'Работает' : 'Заблокирован'}
    </span>
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: '11px', padding: '1px 7px', borderRadius: 4,
      border: `1px solid ${isActive ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
      color: isActive ? '#10b981' : '#ef4444',
      background: isActive ? 'rgba(16,185,129,0.07)' : 'rgba(239,68,68,0.07)',
    }}>
      {isActive ? 'Может играть' : 'Не может играть'}
    </span>
  </div>
);

/* ──────────────────── CREATE MODAL ──────────────────── */
const CreateModal = ({ onClose, onSaved }) => {
  const { toast } = useToast();
  const [tab, setTab] = useState('phone');  // 'phone' | 'new'
  const [form, setForm] = useState({
    phone: '', first_name: '', last_name: '', username: '', password: '', role: 'operator',
  });
  const [showPwd, setShowPwd] = useState(false);
  const [saving, setSaving] = useState(false);
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selected, setSelected] = useState(null);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  // Phone/username search
  useEffect(() => {
    const q = form.phone.trim();
    if (tab !== 'phone' || q.length < 2) { setResults([]); return; }
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const r = await apiFetch(`/api/v1/accounts/users/search/?q=${encodeURIComponent(q)}`);
        setResults(r.results || r || []);
      } catch { setResults([]); }
      finally { setSearching(false); }
    }, 350);
    return () => clearTimeout(t);
  }, [form.phone, tab]);

  const handleSave = async () => {
    setSaving(true);
    try {
      if (tab === 'phone') {
        if (!selected) { toast('Выберите пользователя из списка', { type: 'warning' }); setSaving(false); return; }
        await apiFetch(`/api/v1/accounts/employees/${selected.id}/`, {
          method: 'PATCH',
          body: JSON.stringify({ role: form.role }),
        });
        toast('Сотрудник добавлен', { type: 'success' });
      } else {
        if (!form.username.trim()) { toast('Введите логин', { type: 'warning' }); setSaving(false); return; }
        if (!form.password || form.password.length < 6) { toast('Пароль минимум 6 символов', { type: 'warning' }); setSaving(false); return; }
        await apiFetch('/api/v1/accounts/employees/', {
          method: 'POST',
          body: JSON.stringify({
            username: form.username.trim(),
            password: form.password,
            role: form.role,
            first_name: form.first_name,
            last_name: form.last_name,
            phone: form.phone,
          }),
        });
        toast('Сотрудник создан', { type: 'success' });
      }
      onSaved();
    } catch (e) {
      const msg = e.body
        ? (typeof e.body === 'object' ? Object.values(e.body).flat().join(', ') : String(e.body))
        : e.message;
      toast(msg || 'Ошибка сохранения', { type: 'error' });
    } finally { setSaving(false); }
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, padding: 20,
    }}>
      <div style={{
        background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
        borderRadius: 16, width: '100%', maxWidth: 460,
        boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
        animation: 'modalIn 0.25s ease',
      }}>
        {/* Header */}
        <div style={{ padding: '18px 20px 14px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Добавить сотрудника</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, display: 'flex' }}><X size={18} /></button>
        </div>

        <div style={{ padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Tab switcher */}
          <div style={{ display: 'flex', gap: 4, background: 'var(--bg-dark)', borderRadius: 10, padding: 4 }}>
            {[{ id: 'phone', label: 'Найти пользователя' }, { id: 'new', label: 'Создать аккаунт' }].map(t => (
              <button key={t.id} onClick={() => { setTab(t.id); setSelected(null); setResults([]); }}
                style={{
                  flex: 1, height: 30, borderRadius: 7, border: 'none', cursor: 'pointer',
                  fontFamily: 'inherit', fontSize: '12px', fontWeight: 500,
                  background: tab === t.id ? 'var(--bg-panel)' : 'transparent',
                  color: tab === t.id ? 'var(--text-main)' : 'var(--text-muted)',
                  boxShadow: tab === t.id ? '0 1px 3px rgba(0,0,0,0.3)' : 'none',
                }}>
                {t.label}
              </button>
            ))}
          </div>

          {/* Phone search tab */}
          {tab === 'phone' && (
            <div>
              {selected ? (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px',
                  background: 'rgba(16,185,129,0.08)', borderRadius: 10,
                  border: '1px solid rgba(16,185,129,0.25)',
                }}>
                  <Avatar name={selected.full_name || selected.username} size={32} color="#10b981" bg="rgba(16,185,129,0.15)" />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>{selected.full_name || selected.username}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{selected.phone || selected.username}</div>
                  </div>
                  <button onClick={() => { setSelected(null); setForm(f => ({ ...f, phone: '' })); }}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}>
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <div style={{ position: 'relative' }}>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>
                    Телефон или логин
                  </label>
                  <div style={{ position: 'relative' }}>
                    <Search size={13} style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input style={{ ...iStyle, paddingLeft: 32 }}
                      value={form.phone} onChange={e => set('phone', e.target.value)}
                      placeholder="Введите телефон или логин…" />
                  </div>
                  {form.phone.length >= 2 && (
                    <div style={{
                      position: 'absolute', zIndex: 50, width: '100%', top: '100%', marginTop: 4,
                      background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
                      borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.3)', overflow: 'hidden',
                    }}>
                      {searching && <div style={{ padding: '10px 14px', fontSize: '12px', color: 'var(--text-muted)' }}>Поиск…</div>}
                      {!searching && results.length === 0 && <div style={{ padding: '10px 14px', fontSize: '12px', color: 'var(--text-muted)' }}>Пользователи не найдены</div>}
                      {results.map(u => (
                        <div key={u.id} onClick={() => { setSelected(u); setResults([]); }}
                          style={{ padding: '9px 14px', cursor: 'pointer', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                          onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                          <span style={{ fontWeight: 500 }}>{u.full_name || u.username}</span>
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{u.phone || u.username}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* New account tab */}
          {tab === 'new' && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Имя</label>
                  <input style={iStyle} value={form.first_name} onChange={e => set('first_name', e.target.value)} placeholder="Иван" />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Фамилия</label>
                  <input style={iStyle} value={form.last_name} onChange={e => set('last_name', e.target.value)} placeholder="Петров" />
                </div>
              </div>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>
                  Логин <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <input style={iStyle} value={form.username} onChange={e => set('username', e.target.value)} placeholder="ivan_petrov" />
              </div>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>
                  Пароль <span style={{ color: '#ef4444' }}>*</span>
                </label>
                <div style={{ position: 'relative' }}>
                  <input type={showPwd ? 'text' : 'password'} style={{ ...iStyle, paddingRight: 38 }}
                    value={form.password} onChange={e => set('password', e.target.value)} placeholder="Минимум 6 символов" />
                  <button onClick={() => setShowPwd(v => !v)}
                    style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}>
                    {showPwd ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Телефон</label>
                <input style={iStyle} value={form.phone} onChange={e => set('phone', e.target.value)} placeholder="+7 999 000 00 00" />
              </div>
            </>
          )}

          {/* Role selector */}
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 8 }}>Выберите роль</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {ASSIGN_ROLES.map(r => {
                const active = form.role === r.value;
                return (
                  <button key={r.value} onClick={() => set('role', r.value)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px',
                      borderRadius: 9, border: `1.5px solid ${active ? r.color : 'var(--border-color)'}`,
                      background: active ? r.bg : 'var(--bg-dark)',
                      cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                      transition: 'all 0.15s',
                    }}>
                    <r.icon size={14} color={active ? r.color : 'var(--text-muted)'} />
                    <span style={{ fontSize: '13px', fontWeight: 600, color: active ? r.color : 'var(--text-main)', flex: 1 }}>{r.label}</span>
                    {active && <ChevronRight size={14} color={r.color} />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Save */}
          <button onClick={handleSave} disabled={saving}
            style={{
              height: 40, borderRadius: 9, border: 'none', cursor: saving ? 'default' : 'pointer',
              background: 'var(--primary-color)', color: '#fff',
              fontFamily: 'inherit', fontSize: '13px', fontWeight: 600,
              opacity: saving ? 0.7 : 1, marginTop: 4,
            }}>
            {saving ? 'Сохранение…' : 'Сделать сотрудником'}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ──────────────────── EDIT MODAL ──────────────────── */
const EditModal = ({ emp, onClose, onSaved, onFired }) => {
  const { toast } = useToast();
  const [form, setForm] = useState({
    role: emp.role || 'operator',
    first_name: emp.first_name || '',
    last_name: emp.last_name || '',
  });
  const [saving, setSaving] = useState(false);
  const [firing, setFiring] = useState(false);
  const rc = getRoleConf(form.role);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSave = async () => {
    setSaving(true);
    try {
      await apiFetch(`/api/v1/accounts/employees/${emp.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ role: form.role, first_name: form.first_name, last_name: form.last_name }),
      });
      toast('Изменения сохранены', { type: 'success' });
      onSaved();
    } catch (e) {
      const msg = e.body ? (typeof e.body === 'object' ? Object.values(e.body).flat().join(', ') : String(e.body)) : e.message;
      toast(msg || 'Ошибка', { type: 'error' });
    } finally { setSaving(false); }
  };

  const handleFire = async () => {
    if (!window.confirm(`Уволить ${emp.full_name || emp.username}? Роль сотрудника будет снята.`)) return;
    setFiring(true);
    try {
      await apiFetch(`/api/v1/accounts/employees/${emp.id}/`, { method: 'DELETE' });
      toast(`${emp.full_name || emp.username} уволен(а)`, { type: 'success' });
      onFired(emp.id);
    } catch (e) {
      toast(e.message || 'Ошибка', { type: 'error' });
    } finally { setFiring(false); }
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, padding: 20,
    }}>
      <div style={{
        background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
        borderRadius: 16, width: '100%', maxWidth: 440,
        boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
        animation: 'modalIn 0.25s ease',
      }}>
        {/* Header */}
        <div style={{ padding: '18px 20px 14px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Avatar name={emp.full_name || emp.username} size={34} color={rc.color} bg={rc.bg} />
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700 }}>{emp.full_name || emp.username}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>@{emp.username}</div>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', padding: 4 }}><X size={18} /></button>
        </div>

        <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Name fields */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Имя</label>
              <input style={iStyle} value={form.first_name} onChange={e => set('first_name', e.target.value)} />
            </div>
            <div>
              <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>Фамилия</label>
              <input style={iStyle} value={form.last_name} onChange={e => set('last_name', e.target.value)} />
            </div>
          </div>

          {/* Role selector */}
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 8 }}>Роль</label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {ASSIGN_ROLES.map(r => {
                const active = form.role === r.value;
                return (
                  <button key={r.value} onClick={() => set('role', r.value)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 9, padding: '8px 11px',
                      borderRadius: 8, border: `1.5px solid ${active ? r.color : 'var(--border-color)'}`,
                      background: active ? r.bg : 'var(--bg-dark)',
                      cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                      transition: 'all 0.15s',
                    }}>
                    <r.icon size={13} color={active ? r.color : 'var(--text-muted)'} />
                    <span style={{ fontSize: '12px', fontWeight: 600, color: active ? r.color : 'var(--text-main)', flex: 1 }}>{r.label}</span>
                    {active && <ChevronRight size={13} color={r.color} />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button onClick={handleFire} disabled={firing || saving}
              style={{
                flex: 1, height: 38, borderRadius: 8,
                border: '1.5px solid #ef4444', background: 'transparent',
                color: '#ef4444', fontFamily: 'inherit', fontSize: '13px', fontWeight: 600,
                cursor: firing ? 'default' : 'pointer', opacity: firing ? 0.7 : 1,
              }}>
              {firing ? 'Увольнение…' : 'Уволить'}
            </button>
            <button onClick={handleSave} disabled={saving || firing}
              style={{
                flex: 2, height: 38, borderRadius: 8,
                border: '1px solid var(--border-color)', background: 'var(--bg-dark)',
                color: 'var(--text-main)', fontFamily: 'inherit', fontSize: '13px', fontWeight: 600,
                cursor: saving ? 'default' : 'pointer', opacity: saving ? 0.7 : 1,
              }}>
              {saving ? 'Сохранение…' : 'Изменить'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ──────────────────── ROLES TAB ──────────────────── */
const RolesTab = () => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
    {ALL_ROLES.map(r => (
      <div key={r.value} style={{
        display: 'flex', alignItems: 'flex-start', gap: 14, padding: '14px 16px',
        background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
        borderRadius: 12,
      }}>
        {/* Role icon */}
        <div style={{
          width: 40, height: 40, borderRadius: 10, background: r.bg,
          border: `1px solid ${r.color}30`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <r.icon size={18} color={r.color} />
        </div>
        {/* Info */}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: r.color }}>{r.label}</span>
            {r.readOnly && (
              <span style={{
                fontSize: '10px', padding: '1px 6px', borderRadius: 4,
                background: 'var(--bg-dark)', color: 'var(--text-muted)',
                border: '1px solid var(--border-color)',
              }}>
                Информационная роль
              </span>
            )}
          </div>
          <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexWrap: 'wrap', gap: '4px 12px' }}>
            {r.perms.map((p, i) => (
              <li key={i} style={{
                fontSize: '12px', color: 'var(--text-muted)',
                display: 'flex', alignItems: 'center', gap: 5,
              }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: r.color, flexShrink: 0 }} />
                {p}
              </li>
            ))}
          </ul>
        </div>
      </div>
    ))}
  </div>
);

/* ──────────────────── MAIN COMPONENT ──────────────────── */
const Employees = () => {
  const { toast } = useToast();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState('employees');  // 'employees' | 'roles'
  const [createModal, setCreateModal] = useState(false);
  const [editEmp, setEditEmp] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await apiFetch('/api/v1/accounts/employees/');
      setEmployees(r.results || r || []);
    } catch (e) { toast(e.message || 'Ошибка загрузки', { type: 'error' }); }
    finally { setLoading(false); }
  }, []); // eslint-disable-line

  useEffect(() => { load(); }, [load]);

  const filtered = search
    ? employees.filter(e =>
        (e.username || '').toLowerCase().includes(search.toLowerCase()) ||
        (e.full_name || '').toLowerCase().includes(search.toLowerCase()) ||
        (e.phone || '').includes(search))
    : employees;

  return (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <style>{`
        @keyframes modalIn {
          from { transform: scale(0.93) translateY(16px); opacity: 0; }
          to   { transform: scale(1) translateY(0); opacity: 1; }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .emp-row:hover { background: var(--hover-overlay) !important; cursor: pointer; }
        .emp-row td { padding: 12px 14px; vertical-align: middle; border-bottom: 1px solid var(--border-color); }
        .emp-row:last-child td { border-bottom: none; }
      `}</style>

      {/* Page header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700, color: 'var(--text-main)' }}>Сотрудники</h2>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
            Управление персоналом и правами доступа
          </p>
        </div>
        <button onClick={() => setCreateModal(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
            borderRadius: 9, border: 'none', cursor: 'pointer',
            background: 'var(--primary-color)', color: '#fff',
            fontFamily: 'inherit', fontSize: '13px', fontWeight: 600,
          }}>
          <Plus size={15} /> Добавить сотрудника
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '1px solid var(--border-color)' }}>
        {[
          { id: 'employees', label: `Сотрудники ${employees.length > 0 ? employees.length : ''}` },
          { id: 'roles',     label: `Роли ${ALL_ROLES.length}` },
        ].map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            style={{
              padding: '9px 18px', fontFamily: 'inherit', fontSize: '13px', fontWeight: 600,
              border: 'none', background: 'none', cursor: 'pointer',
              color: activeTab === t.id ? 'var(--primary-color)' : 'var(--text-muted)',
              borderBottom: activeTab === t.id ? '2px solid var(--primary-color)' : '2px solid transparent',
              marginBottom: -1,
              transition: 'all 0.15s',
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Employees tab */}
      {activeTab === 'employees' && (
        <>
          {/* Search + refresh */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
            <div style={{ position: 'relative', flex: 1, maxWidth: 280 }}>
              <Search size={13} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Поиск по имени, логину, телефону…"
                style={{ ...iStyle, paddingLeft: 30, height: 36, fontSize: '12px' }} />
            </div>
            <button onClick={load} disabled={loading}
              style={{
                display: 'flex', alignItems: 'center', gap: 5, padding: '0 12px', height: 36,
                borderRadius: 8, border: '1px solid var(--border-color)', background: 'var(--bg-dark)',
                color: 'var(--text-muted)', fontFamily: 'inherit', fontSize: '12px', cursor: 'pointer',
              }}>
              <RefreshCw size={13} style={{ animation: loading ? 'spin 0.8s linear infinite' : 'none' }} />
              Обновить
            </button>
          </div>

          {/* Table */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: '60px 0', color: 'var(--text-muted)', fontSize: '13px' }}>
              Загрузка…
            </div>
          ) : filtered.length === 0 ? (
            <div style={{
              textAlign: 'center', padding: '60px 0',
              background: 'var(--bg-panel)', borderRadius: 12, border: '1px solid var(--border-color)',
            }}>
              <User size={40} style={{ opacity: 0.15, marginBottom: 12, display: 'block', margin: '0 auto 12px' }} />
              <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                {search ? 'Никого не найдено' : 'Сотрудников пока нет'}
              </div>
              {!search && (
                <button onClick={() => setCreateModal(true)}
                  style={{ marginTop: 12, padding: '7px 16px', borderRadius: 8, border: 'none', cursor: 'pointer', background: 'var(--primary-color)', color: '#fff', fontFamily: 'inherit', fontSize: '12px', fontWeight: 600 }}>
                  Добавить первого
                </button>
              )}
            </div>
          ) : (
            <div style={{ background: 'var(--bg-panel)', borderRadius: 12, border: '1px solid var(--border-color)', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-dark)' }}>
                    {['Сотрудник', 'Никнейм', 'Роль', 'Статус', 'Дата создания'].map(h => (
                      <th key={h} style={{
                        padding: '10px 14px', textAlign: 'left', fontSize: '11px', fontWeight: 600,
                        color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.4px',
                        borderBottom: '1px solid var(--border-color)',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(emp => {
                    const rc = getRoleConf(emp.role);
                    return (
                      <tr key={emp.id} className="emp-row" onClick={() => setEditEmp(emp)} style={{ background: 'transparent', transition: 'background 0.12s' }}>
                        {/* Сотрудник */}
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <Avatar name={emp.full_name || emp.username} size={36} color={rc.color} bg={rc.bg} />
                            <div>
                              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>
                                {emp.full_name || emp.username}
                              </div>
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                                {emp.phone || emp.email || '—'}
                              </div>
                            </div>
                          </div>
                        </td>

                        {/* Никнейм */}
                        <td style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                          @{emp.username}
                        </td>

                        {/* Роль */}
                        <td>
                          <RoleBadge role={emp.role} />
                        </td>

                        {/* Статус */}
                        <td>
                          <StatusBadges isActive={true} />
                        </td>

                        {/* Дата создания */}
                        <td style={{ fontSize: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                          {emp.created_at || '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Roles tab */}
      {activeTab === 'roles' && <RolesTab />}

      {/* Create modal */}
      {createModal && (
        <CreateModal
          onClose={() => setCreateModal(false)}
          onSaved={() => { setCreateModal(false); load(); }}
        />
      )}

      {/* Edit modal */}
      {editEmp && (
        <EditModal
          emp={editEmp}
          onClose={() => setEditEmp(null)}
          onSaved={() => { setEditEmp(null); load(); }}
          onFired={(id) => { setEditEmp(null); setEmployees(prev => prev.filter(e => e.id !== id)); }}
        />
      )}
    </div>
  );
};

export default Employees;
