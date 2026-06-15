import { useState, useEffect, useCallback } from 'react';
import {
  LayoutGrid, Building2, Crown, Users, Tag, LogOut, RefreshCw, X,
  TrendingUp, AlertTriangle, Clock, ShieldCheck, Search, Edit2,
} from 'lucide-react';
import { apiFetch, logout as apiLogout, decodeJwt } from '../api/client';
import { useToast } from '../components/Toast';

// Current platform admin's own user id (to prevent self block / self-demote)
const SELF_ID = (() => {
  try { return String(decodeJwt(localStorage.getItem('access_token'))?.user_id || ''); }
  catch { return ''; }
})();

const fmtRub = (v) => Number(v || 0).toLocaleString('ru-RU') + ' сум';
const fmtDate = (iso) => { try { return new Date(iso).toLocaleDateString('ru-RU'); } catch { return '—'; } };

const STATUS = {
  trial:    { label: 'Триал',        color: '#818cf8', bg: 'rgba(99,102,241,0.15)' },
  active:   { label: 'Активна',      color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  promised: { label: 'Обещанный',    color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  expired:  { label: 'Истекла',      color: '#9ca3af', bg: 'rgba(156,163,175,0.15)' },
  blocked:  { label: 'Заблокирован', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
};

const NAV = [
  { id: 'dashboard', label: 'Обзор',      icon: LayoutGrid },
  { id: 'clubs',     label: 'Клубы',      icon: Building2 },
  { id: 'plans',     label: 'Тарифы',     icon: Tag },
  { id: 'users',     label: 'Пользователи', icon: Users },
  { id: 'employees', label: 'Сотрудники', icon: Crown },
];

/* ── Metric card ── */
const Metric = ({ icon: Icon, label, value, color = '#6366f1' }) => (
  <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
    borderRadius: 12, padding: '16px 18px', flex: 1, minWidth: 150 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
      <span style={{ width: 30, height: 30, borderRadius: 8, background: `${color}22`,
        display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon size={15} color={color} /></span>
      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</span>
    </div>
    <div style={{ fontSize: 24, fontWeight: 700 }}>{value}</div>
  </div>
);

/* ════════════════ DASHBOARD ════════════════ */
const Dashboard = () => {
  const [d, setD] = useState(null);
  useEffect(() => { apiFetch('/api/v1/platform/dashboard/').then(setD).catch(() => {}); }, []);
  if (!d) return <div style={{ padding: 40, color: 'var(--text-muted)' }}>Загрузка…</div>;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <Metric icon={Building2}  label="Всего клубов"      value={d.total_clubs} />
        <Metric icon={ShieldCheck} label="Активных подписок" value={d.active_subs} color="#10b981" />
        <Metric icon={Clock}      label="На триале"         value={d.trials} color="#818cf8" />
        <Metric icon={TrendingUp} label="MRR (потенц.)"     value={fmtRub(d.mrr)} color="#10b981" />
      </div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <Metric icon={AlertTriangle} label="Истекает триал (≤7д)" value={d.expiring_trials} color="#f59e0b" />
        <Metric icon={AlertTriangle} label="Просроченные долги"    value={d.overdue_debts} color="#ef4444" />
        <Metric icon={Building2}     label="Новых клубов за месяц" value={d.new_clubs_this_month} color="#6366f1" />
        <Metric icon={X}             label="Заблокировано"         value={d.blocked} color="#ef4444" />
      </div>
    </div>
  );
};

/* ════════════════ CLUBS ════════════════ */
const ClubsPage = () => {
  const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const [search, setSearch] = useState('');
  const [statusF, setStatusF] = useState('');
  const [manage, setManage] = useState(null); // club row
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    let url = '/api/v1/platform/clubs/?';
    if (search) url += `search=${encodeURIComponent(search)}&`;
    if (statusF) url += `status=${statusF}`;
    apiFetch(url).then(r => setRows(r.results || [])).catch(() => {});
  }, [search, statusF]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);

  // Enter a club as platform operator (impersonation, audited server-side)
  const impersonate = async (club) => {
    try {
      await apiFetch(`/api/v1/platform/clubs/${club.id}/impersonate/`, { method: 'POST' });
      localStorage.setItem('active_club_id', String(club.id));
      localStorage.setItem('active_club_name', club.name);
      localStorage.setItem('impersonate_mode', '1');
      window.location.href = '/';
    } catch (e) { toast(e.body?.error || e.message, { type: 'error' }); }
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Поиск клуба/владельца"
            style={{ paddingLeft: 32, height: 34, width: 240, background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
              borderRadius: 8, color: 'var(--text-main)', fontSize: 13, fontFamily: 'inherit' }} />
        </div>
        <select value={statusF} onChange={e => setStatusF(e.target.value)}
          style={{ height: 34, padding: '0 10px', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
            borderRadius: 8, color: 'var(--text-main)', fontSize: 13, fontFamily: 'inherit' }}>
          <option value="">Все статусы</option>
          {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <button className="btn btn-secondary" onClick={load}><RefreshCw size={14} /></button>
        <button className="btn btn-primary" style={{ marginLeft: 'auto' }} onClick={() => setCreating(true)}>+ Создать клуб</button>
      </div>

      <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 12, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead><tr style={{ borderBottom: '1px solid var(--border-color)' }}>
            {['Клуб', 'Владелец', 'Тариф', 'Статус', 'ПК', 'Выручка', 'Истекает', ''].map(c => (
              <th key={c} style={{ padding: '11px 14px', textAlign: c === 'ПК' || c === 'Выручка' ? 'right' : 'left',
                fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>{c}</th>
            ))}
          </tr></thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={8} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Клубов нет</td></tr>}
            {rows.map(c => {
              const st = STATUS[c.status] || STATUS.active;
              return (
                <tr key={c.id} style={{ borderBottom: '1px solid var(--border-row)' }}>
                  <td style={{ padding: '11px 14px', fontWeight: 600 }}>{c.name}
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>{c.city}</div></td>
                  <td style={{ padding: '11px 14px' }}>{c.owner}
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.owner_phone}</div></td>
                  <td style={{ padding: '11px 14px' }}>{c.plan}</td>
                  <td style={{ padding: '11px 14px' }}>
                    <span style={{ padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600, background: st.bg, color: st.color }}>{st.label}</span>
                  </td>
                  <td style={{ padding: '11px 14px', textAlign: 'right' }}>{c.pc_count}</td>
                  <td style={{ padding: '11px 14px', textAlign: 'right', color: '#10b981', fontWeight: 600 }}>{fmtRub(c.revenue)}</td>
                  <td style={{ padding: '11px 14px', color: 'var(--text-muted)' }}>{c.expires_at ? fmtDate(c.expires_at) : '—'}</td>
                  <td style={{ padding: '11px 14px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button className="btn btn-secondary" style={{ fontSize: 12, padding: '5px 10px', marginRight: 6 }}
                      onClick={() => impersonate(c)} title="Открыть панель клуба под вашими правами">↪ Войти</button>
                    <button className="btn btn-secondary" style={{ fontSize: 12, padding: '5px 10px' }}
                      onClick={() => setManage(c)}>Управление</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {manage && <ManageClubModal club={manage} onClose={() => setManage(null)} onDone={() => { setManage(null); load(); }} toast={toast} />}
      {creating && <CreateClubModal onClose={() => setCreating(false)} onDone={() => { setCreating(false); load(); }} toast={toast} />}
    </div>
  );
};

const CreateClubModal = ({ onClose, onDone, toast }) => {
  const [f, setF] = useState({ name: '', city: '', owner_username: '', owner_password: '', owner_phone: '', trial_days: 14 });
  const [busy, setBusy] = useState(false);
  const up = (k, v) => setF(p => ({ ...p, [k]: v }));
  const inp = { width: '100%', boxSizing: 'border-box', height: 38, padding: '0 12px', marginBottom: 12,
    background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: 8, color: 'var(--text-main)', fontSize: 13, fontFamily: 'inherit' };
  const submit = async () => {
    if (!f.name.trim()) { toast('Введите название клуба', { type: 'warning' }); return; }
    if (!f.owner_username.trim()) { toast('Введите логин владельца', { type: 'warning' }); return; }
    if ((f.owner_password || '').length < 6) { toast('Пароль владельца — минимум 6 символов', { type: 'warning' }); return; }
    setBusy(true);
    try {
      const r = await apiFetch('/api/v1/platform/clubs/create/', {
        method: 'POST',
        body: JSON.stringify({ ...f, trial_days: Number(f.trial_days) || 14 }),
      });
      toast(`Клуб «${r.name}» создан · токен ${r.token}`, { type: 'success' });
      onDone();  // unmounts modal — don't touch state after this
    } catch (e) {
      toast(e.body?.error || e.message, { type: 'error' });
      setBusy(false);
    }
  };
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 900,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 14, padding: 24, width: 420, border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>Новый клуб</h3><button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>
        <label style={{ fontSize: 12, color: 'var(--text-muted)' }}>Название клуба *</label>
        <input style={inp} value={f.name} onChange={e => up('name', e.target.value)} autoFocus />
        <label style={{ fontSize: 12, color: 'var(--text-muted)' }}>Город</label>
        <input style={inp} value={f.city} onChange={e => up('city', e.target.value)} />
        <div style={{ borderTop: '1px solid var(--border-row)', margin: '4px 0 12px' }} />
        <label style={{ fontSize: 12, color: 'var(--text-muted)' }}>Логин владельца *</label>
        <input style={inp} value={f.owner_username} onChange={e => up('owner_username', e.target.value)} />
        <label style={{ fontSize: 12, color: 'var(--text-muted)' }}>Пароль владельца * (мин. 6)</label>
        <input style={inp} value={f.owner_password} onChange={e => up('owner_password', e.target.value)} />
        <label style={{ fontSize: 12, color: 'var(--text-muted)' }}>Телефон владельца</label>
        <input style={inp} value={f.owner_phone} onChange={e => up('owner_phone', e.target.value)} placeholder="+7..." />
        <label style={{ fontSize: 12, color: 'var(--text-muted)' }}>Дней триала</label>
        <input type="number" style={inp} value={f.trial_days} onChange={e => up('trial_days', e.target.value)} />
        <button className="btn btn-primary" style={{ width: '100%', height: 44 }} onClick={submit} disabled={busy}>
          {busy ? 'Создание…' : 'Создать клуб + владельца'}
        </button>
      </div>
    </div>
  );
};

const ManageClubModal = ({ club, onClose, onDone, toast }) => {
  const [busy, setBusy] = useState(false);
  const [balance, setBalance] = useState(null);
  const [amount, setAmount] = useState('');
  const [topping, setTopping] = useState(false);

  useEffect(() => {
    apiFetch(`/api/v1/clubs/${club.id}/wallet/`).then(w => setBalance(w.balance)).catch(() => setBalance('0'));
  }, [club.id]);

  const topup = async () => {
    const a = Number(amount);
    if (!Number.isFinite(a) || a <= 0) { toast('Введите корректную сумму', { type: 'warning' }); return; }
    setTopping(true);
    try {
      const r = await apiFetch(`/api/v1/clubs/${club.id}/wallet/topup/`, {
        method: 'POST', body: JSON.stringify({ amount: a, comment: 'Пополнение через /platform' }),
      });
      setBalance(r.balance); setAmount('');
      toast(`Баланс пополнен. Сейчас: ${Number(r.balance).toLocaleString('ru-RU')} сум`, { type: 'success' });
      onDone && onDone();  // refresh the clubs table (balance/plan columns)
    } catch (e) {
      const b = e.body || {};
      const msg = b.error || b.amount || b.balance || (Array.isArray(b) ? b[0] : null) || e.message;
      toast(Array.isArray(msg) ? msg[0] : msg, { type: 'error' });
    }
    finally { setTopping(false); }
  };

  const act = async (action, extra = {}) => {
    setBusy(true);
    try {
      await apiFetch(`/api/v1/platform/clubs/${club.id}/manage/`, {
        method: 'POST', body: JSON.stringify({ action, ...extra }),
      });
      toast('Готово', { type: 'success' });
      onDone();  // unmounts modal — don't touch state after
    } catch (e) {
      toast(e.body?.error || e.message, { type: 'error' });
      setBusy(false);
    }
  };
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 900,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 14, padding: 24, width: 420, border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>{club.name}</h3>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
          Владелец: {club.owner} · Тариф: {club.plan} · Статус: {STATUS[club.status]?.label}
        </div>

        {/* Balance + top-up */}
        <div style={{ background: 'var(--bg-dark)', borderRadius: 10, padding: 14, marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Баланс клуба</span>
            <span style={{ fontSize: 18, fontWeight: 800 }}>
              {balance == null ? '…' : Number(balance).toLocaleString('ru-RU') + ' сум'}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <input type="number" value={amount} onChange={e => setAmount(e.target.value)} placeholder="Сумма пополнения"
              style={{ flex: 1, height: 38, padding: '0 12px', background: 'var(--bg-panel)',
                border: '1px solid var(--border-color)', borderRadius: 8, color: 'var(--text-main)', fontSize: 14 }} />
            <button className="btn btn-primary" disabled={topping} onClick={topup}>
              {topping ? '…' : 'Пополнить'}
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button className="btn btn-secondary" disabled={busy} onClick={() => act('extend_trial', { days: 14 })}>Продлить триал +14 дней</button>
          <button className="btn btn-primary" disabled={busy} onClick={() => act('activate', { tier: 'starter', days: 30 })}>Активировать Starter (30 дней)</button>
          <button className="btn btn-primary" disabled={busy} onClick={() => act('activate', { tier: 'business', days: 30 })} style={{ background: '#f59e0b', borderColor: '#f59e0b' }}>Активировать Business (30 дней)</button>
          {club.status === 'blocked' ? (
            <button className="btn btn-secondary" disabled={busy} onClick={() => act('unblock')} style={{ color: '#10b981' }}>Разблокировать</button>
          ) : (
            <button className="btn btn-secondary" disabled={busy} onClick={() => act('block')} style={{ color: '#ef4444' }}>Заблокировать</button>
          )}
        </div>
      </div>
    </div>
  );
};

/* ════════════════ PLANS ════════════════ */
const PlansPage = () => {
  const { toast } = useToast();
  const [plans, setPlans] = useState([]);
  const load = () => apiFetch('/api/v1/platform/plans/').then(setPlans).catch(() => {});
  useEffect(() => { load(); }, []);
  const savePrice = async (p, price) => {
    try { await apiFetch(`/api/v1/platform/plans/${p.id}/`, { method: 'PATCH', body: JSON.stringify({ monthly_price: Number(price) }) }); toast('Сохранено', { type: 'success' }); load(); }
    catch { toast('Ошибка', { type: 'error' }); }
  };
  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
      {plans.map(p => (
        <div key={p.id} style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
          borderRadius: 14, padding: 22, width: 240 }}>
          <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{p.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
            {p.max_pcs === 0 ? 'Без лимита ПК' : `до ${p.max_pcs} ПК`} · {p.clubs_count} клубов
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <input type="number" defaultValue={p.monthly_price}
              onBlur={e => Number(e.target.value) !== Number(p.monthly_price) && savePrice(p, e.target.value)}
              style={{ width: 110, height: 36, padding: '0 10px', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                borderRadius: 8, color: 'var(--text-main)', fontSize: 16, fontWeight: 700, fontFamily: 'inherit' }} />
            <span style={{ color: 'var(--text-muted)' }}>сум/мес</span>
          </div>
          <div style={{ fontSize: 11, color: p.is_active ? '#10b981' : 'var(--text-muted)' }}>
            {p.is_active ? '● Активен' : '○ Отключён'}
          </div>
        </div>
      ))}
    </div>
  );
};

/* ════════════════ USERS ════════════════ */
const UsersPage = () => {
  const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const [kind, setKind] = useState('all');
  const [search, setSearch] = useState('');
  const load = useCallback(() => {
    apiFetch(`/api/v1/platform/users/?kind=${kind}&search=${encodeURIComponent(search)}`)
      .then(r => setRows(r.results || [])).catch(() => {});
  }, [kind, search]);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [load]);
  const TYPE = { user: 'Клиент', owner: 'Владелец', manager: 'Менеджер', operator: 'Оператор', admin: 'Админ' };

  const act = async (u, action, extra = {}) => {
    try {
      await apiFetch(`/api/v1/platform/users/${u.id}/action/`, { method: 'POST', body: JSON.stringify({ action, ...extra }) });
      toast('Готово', { type: 'success' }); load();
    } catch (e) { toast(e.body?.error || e.message, { type: 'error' }); }
  };
  const resetPw = (u) => {
    const pw = window.prompt(`Новый пароль для ${u.username} (мин. 6):`);
    if (pw && pw.length >= 6) act(u, 'reset_password', { password: pw });
    else if (pw !== null) toast('Минимум 6 символов', { type: 'warning' });
  };
  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        {[['all','Все'],['client','Клиенты'],['owner','Владельцы'],['staff','Сотрудники'],['admin','Админы']].map(([k,l]) => (
          <button key={k} onClick={() => setKind(k)}
            style={{ padding: '6px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', border: 'none', fontFamily: 'inherit',
              background: kind === k ? 'var(--accent)' : 'var(--hover-overlay)', color: kind === k ? '#fff' : 'var(--text-muted)' }}>{l}</button>
        ))}
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Поиск"
          style={{ marginLeft: 'auto', height: 34, padding: '0 12px', width: 200, background: 'var(--bg-dark)',
            border: '1px solid var(--border-color)', borderRadius: 8, color: 'var(--text-main)', fontSize: 13, fontFamily: 'inherit' }} />
      </div>
      <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 12, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead><tr style={{ borderBottom: '1px solid var(--border-color)' }}>
            {['Логин', 'Имя', 'Телефон', 'Тип', 'Статус', 'Действия'].map(c => (
              <th key={c} style={{ padding: '11px 14px', textAlign: c === 'Действия' ? 'right' : 'left', fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>{c}</th>
            ))}
          </tr></thead>
          <tbody>
            {rows.map(u => (
              <tr key={u.id} style={{ borderBottom: '1px solid var(--border-row)', opacity: u.is_active ? 1 : 0.55 }}>
                <td style={{ padding: '10px 14px', fontWeight: 600 }}>{u.username}</td>
                <td style={{ padding: '10px 14px' }}>{u.full_name || '—'}</td>
                <td style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>{u.phone || '—'}</td>
                <td style={{ padding: '10px 14px' }}>{TYPE[u.user_type] || u.user_type}</td>
                <td style={{ padding: '10px 14px' }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: u.is_active ? '#10b981' : '#ef4444' }}>
                    {u.is_active ? 'Активен' : 'Заблокирован'}</span>
                </td>
                <td style={{ padding: '10px 14px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                  {String(u.id) === SELF_ID ? (
                    <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>это вы</span>
                  ) : (
                    <>
                      <button className="btn btn-secondary" style={{ fontSize: 11, padding: '4px 9px', marginRight: 5 }}
                        onClick={() => resetPw(u)}>🔑 Пароль</button>
                      {u.is_active ? (
                        <button className="btn btn-secondary" style={{ fontSize: 11, padding: '4px 9px', marginRight: 5, color: '#ef4444' }}
                          onClick={() => act(u, 'block')}>Блок</button>
                      ) : (
                        <button className="btn btn-secondary" style={{ fontSize: 11, padding: '4px 9px', marginRight: 5, color: '#10b981' }}
                          onClick={() => act(u, 'unblock')}>Разблок</button>
                      )}
                      {u.user_type === 'admin' ? (
                        <button className="btn btn-secondary" style={{ fontSize: 11, padding: '4px 9px' }}
                          onClick={() => act(u, 'unset_admin')}>− Админ</button>
                      ) : (
                        <button className="btn btn-secondary" style={{ fontSize: 11, padding: '4px 9px' }}
                          onClick={() => window.confirm(`Сделать ${u.username} платформенным админом?`) && act(u, 'set_admin')}>+ Админ</button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/* ════════════════ EMPLOYEES ════════════════ */
const EmployeesPage = () => {
  const [rows, setRows] = useState([]);
  useEffect(() => { apiFetch('/api/v1/platform/employees/').then(r => setRows(r.results || [])).catch(() => {}); }, []);
  const ROLE = { owner: 'Владелец', manager: 'Менеджер', operator: 'Оператор', sysadmin: 'Сисадмин', accountant: 'Бухгалтер' };
  return (
    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 12, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead><tr style={{ borderBottom: '1px solid var(--border-color)' }}>
          {['Сотрудник', 'Клуб', 'Роль'].map(c => (
            <th key={c} style={{ padding: '11px 14px', textAlign: 'left', fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>{c}</th>
          ))}
        </tr></thead>
        <tbody>
          {rows.map((m, i) => (
            <tr key={i} style={{ borderBottom: '1px solid var(--border-row)' }}>
              <td style={{ padding: '10px 14px', fontWeight: 600 }}>{m.username}</td>
              <td style={{ padding: '10px 14px' }}>{m.club}</td>
              <td style={{ padding: '10px 14px' }}>
                <span style={{ padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 600,
                  background: 'rgba(99,102,241,0.12)', color: '#818cf8' }}>{ROLE[m.role] || m.role}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

/* ════════════════ MAIN ════════════════ */
const PlatformApp = () => {
  const [page, setPage] = useState('dashboard');
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-dark)' }}>
      {/* Sidebar */}
      <aside style={{ width: 220, background: 'var(--bg-panel)', borderRight: '1px solid var(--border-color)',
        display: 'flex', flexDirection: 'column', padding: '16px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 8px 18px' }}>
          <div style={{ width: 34, height: 34, borderRadius: 9, background: 'linear-gradient(135deg,#6366f1,#a855f7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center' }}><ShieldCheck size={18} color="#fff" /></div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 14 }}>PCHub</div>
            <div style={{ fontSize: 10, color: '#f59e0b', fontWeight: 700, letterSpacing: 1 }}>PLATFORM</div>
          </div>
        </div>
        {NAV.map(n => {
          const Icon = n.icon; const active = page === n.id;
          return (
            <button key={n.id} onClick={() => setPage(n.id)}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 9,
                marginBottom: 2, cursor: 'pointer', border: 'none', fontFamily: 'inherit', fontSize: 13, fontWeight: 500, textAlign: 'left',
                background: active ? 'var(--accent-dim, rgba(99,102,241,0.15))' : 'transparent',
                color: active ? 'var(--accent)' : 'var(--text-muted)' }}>
              <Icon size={16} /> {n.label}
            </button>
          );
        })}
        <button onClick={() => { apiLogout(); window.location.reload(); }}
          style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px',
            borderRadius: 9, cursor: 'pointer', border: 'none', fontFamily: 'inherit', fontSize: 13,
            background: 'transparent', color: 'var(--text-muted)' }}>
          <LogOut size={16} /> Выйти
        </button>
      </aside>

      {/* Content */}
      <main style={{ flex: 1, padding: '24px 28px', overflowY: 'auto' }}>
        <h2 style={{ margin: '0 0 20px', fontSize: 22, fontWeight: 700 }}>
          {NAV.find(n => n.id === page)?.label}
        </h2>
        {page === 'dashboard' && <Dashboard />}
        {page === 'clubs'     && <ClubsPage />}
        {page === 'plans'     && <PlansPage />}
        {page === 'users'     && <UsersPage />}
        {page === 'employees' && <EmployeesPage />}
      </main>
    </div>
  );
};

export default PlatformApp;
