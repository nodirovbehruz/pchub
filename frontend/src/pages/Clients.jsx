import { useState, useEffect, useCallback } from 'react';
import {
  Users, Search, Plus, CreditCard, Clock, Wifi, WifiOff,
  X, RefreshCw, Edit2, ShieldOff, Percent, UserPlus, Download,
  PlayCircle, StopCircle, Timer,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

const fmtMins = (m) => {
  const h = Math.floor(m / 60);
  const min = m % 60;
  return h > 0 ? `${h}ч ${min > 0 ? min + 'м' : ''}` : `${min || 0}м`;
};

const iStyle = {
  width: '100%', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
  borderRadius: '8px', padding: '10px 12px', color: 'var(--text-light)', fontSize: '13px',
  fontFamily: 'inherit', boxSizing: 'border-box',
};

// ── Deposit modal ─────────────────────────────────────────────────────────────
const DepositModal = ({ client, onClose, onSuccess }) => {
  const { toast } = useToast();
  const [amount, setAmount]           = useState('');
  const [paymentMethod, setPayMethod] = useState('cash');
  const [note, setNote]               = useState('');
  const [loading, setLoading]         = useState(false);

  const clubId = localStorage.getItem('active_club_id');
  const deposit = Number(client.deposit_money || 0);

  const handleDeposit = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      toast('Введите сумму', { type: 'warning' }); return;
    }
    setLoading(true);
    try {
      await apiFetch('/api/v1/billing/admin/topup/', {
        method: 'POST',
        body: JSON.stringify({
          user_id: String(client.id),
          minutes: 0,
          amount_paid: parseFloat(amount),
          payment_method: paymentMethod,
          note,
          club: clubId,
        }),
      });
      toast(`Депозит пополнен на ${parseFloat(amount).toLocaleString('ru-RU')} сум`, { type: 'success' });
      onSuccess(); onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка пополнения', { type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: '14px', padding: '24px',
        width: '400px', maxWidth: '90vw', border: '1px solid var(--border-color)' }}>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ margin: 0 }}>Пополнение депозита</h3>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>

        {/* Client info */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 14px',
          background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
          borderRadius: '10px', marginBottom: '20px' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '50%', flexShrink: 0,
            background: 'linear-gradient(135deg,#6366f1,#a855f7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontWeight: 700, fontSize: '16px' }}>
            {(client.username || '?')[0].toUpperCase()}
          </div>
          <div>
            <div style={{ fontWeight: 600 }}>{client.username}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Депозит сейчас: <strong style={{ color: deposit > 0 ? '#f59e0b' : 'var(--text-muted)' }}>
                {deposit.toLocaleString('ru-RU')} сум
              </strong>
            </div>
          </div>
        </div>

        {/* Amount */}
        <div style={{ marginBottom: '14px' }}>
          <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
            Сумма пополнения, сум *
          </label>
          <input type="number" placeholder="0" min="0" value={amount}
            onChange={e => setAmount(e.target.value)} style={iStyle} autoFocus />
          {amount && parseFloat(amount) > 0 && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Депозит станет: <strong style={{ color: '#f59e0b' }}>
                {(deposit + parseFloat(amount)).toLocaleString('ru-RU')} сум
              </strong>
            </div>
          )}
        </div>

        {/* Payment method */}
        <div style={{ marginBottom: '14px' }}>
          <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>
            Способ оплаты
          </label>
          <div style={{ display: 'flex', gap: '6px' }}>
            {[{ v: 'cash', l: '💵 Наличные' }, { v: 'card', l: '💳 Карта' }, { v: 'transfer', l: '📲 Перевод' }].map(m => (
              <button key={m.v} type="button" onClick={() => setPayMethod(m.v)}
                style={{ flex: 1, padding: '7px 10px', borderRadius: '6px', fontSize: '12px',
                  cursor: 'pointer', fontFamily: 'inherit',
                  background: paymentMethod === m.v ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.04)',
                  border: `1px solid ${paymentMethod === m.v ? '#10b981' : 'var(--border-color)'}`,
                  color: paymentMethod === m.v ? '#10b981' : 'var(--text-muted)' }}>
                {m.l}
              </button>
            ))}
          </div>
        </div>

        {/* Comment */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
            Комментарий
          </label>
          <input type="text" placeholder="Необязательно..." value={note}
            onChange={e => setNote(e.target.value)} style={iStyle} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Отмена</button>
          <button className="btn btn-primary" onClick={handleDeposit} disabled={loading || !amount}>
            {loading ? 'Зачисление...' : `Пополнить на ${parseFloat(amount || 0).toLocaleString('ru-RU')} сум`}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Add client modal ──────────────────────────────────────────────────────────
const AddClientModal = ({ clubId, onClose, onSuccess }) => {
  const { toast } = useToast();
  const [username,   setUsername]   = useState('');
  const [phone,      setPhone]      = useState('');
  const [firstName,  setFirstName]  = useState('');
  const [lastName,   setLastName]   = useState('');
  const [email,      setEmail]      = useState('');
  const [password,   setPassword]   = useState('');
  const [loading,    setLoading]    = useState(false);

  const handleCreate = async () => {
    if (!username.trim()) {
      toast('Введите логин клиента', { type: 'warning' }); return;
    }
    setLoading(true);
    try {
      await apiFetch('/api/v1/accounts/clients/', {
        method: 'POST',
        body: JSON.stringify({
          username: username.trim(),
          phone:      phone.trim(),
          first_name: firstName.trim(),
          last_name:  lastName.trim(),
          email:      email.trim(),
          password:   password.trim() || undefined,
          club:       clubId,
        }),
      });
      toast(`Клиент «${username.trim()}» добавлен`, { type: 'success' });
      onSuccess(); onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка создания клиента', { type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: '14px', padding: '24px',
        width: '460px', maxWidth: '90vw', border: '1px solid var(--border-color)' }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserPlus size={18} /> Новый клиент
          </h3>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>

        {/* Login (required) */}
        <div style={{ marginBottom: '14px' }}>
          <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
            Логин <span style={{ color: '#ef4444' }}>*</span>
          </label>
          <input type="text" placeholder="например: +79001234567 или nickname"
            value={username} onChange={(e) => setUsername(e.target.value)} style={iStyle}
            autoFocus />
        </div>

        {/* First + Last name in a row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Имя</label>
            <input type="text" placeholder="Иван" value={firstName}
              onChange={(e) => setFirstName(e.target.value)} style={iStyle} />
          </div>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Фамилия</label>
            <input type="text" placeholder="Иванов" value={lastName}
              onChange={(e) => setLastName(e.target.value)} style={iStyle} />
          </div>
        </div>

        {/* Phone */}
        <div style={{ marginBottom: '14px' }}>
          <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Телефон</label>
          <input type="tel" placeholder="+79001234567" value={phone}
            onChange={(e) => setPhone(e.target.value)} style={iStyle} />
        </div>

        {/* Email */}
        <div style={{ marginBottom: '14px' }}>
          <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Email</label>
          <input type="email" placeholder="ivan@example.com" value={email}
            onChange={(e) => setEmail(e.target.value)} style={iStyle} />
        </div>

        {/* Password */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
            Пароль
          </label>
          <input type="text" placeholder="Если пусто — пароль = логин"
            value={password} onChange={(e) => setPassword(e.target.value)} style={iStyle} />
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            💡 Если не заполнить, пароль будет равен логину
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Отмена</button>
          <button className="btn btn-primary" onClick={handleCreate} disabled={loading}>
            {loading ? 'Создание...' : 'Добавить клиента'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Start postpaid modal ──────────────────────────────────────────────────────
const PostpaidStartModal = ({ client, onClose, onSuccess }) => {
  const { toast } = useToast();
  const [rate, setRate]       = useState('100');
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    const r = parseFloat(rate);
    if (!r || r <= 0) { toast('Введите ставку за час', { type: 'warning' }); return; }
    setLoading(true);
    try {
      await apiFetch('/api/v1/billing/admin/postpaid/start/', {
        method: 'POST',
        body: JSON.stringify({ user_id: String(client.id), rate_per_hour: r }),
      });
      toast(`Постоплата для ${client.username} запущена`, { type: 'success' });
      onSuccess(); onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка запуска постоплаты', { type: 'error' });
    } finally { setLoading(false); }
  };

  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.6)',
      display:'flex', alignItems:'center', justifyContent:'center', zIndex:900 }}
      onClick={(e) => { if (e.target===e.currentTarget) onClose(); }}>
      <div style={{ background:'var(--bg-panel)', borderRadius:'14px', padding:'24px',
        width:'400px', maxWidth:'90vw', border:'1px solid var(--border-color)' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px' }}>
          <h3 style={{ margin:0, display:'flex', alignItems:'center', gap:'8px' }}>
            <PlayCircle size={18} color="#f59e0b"/> Запустить постоплату
          </h3>
          <button className="icon-btn" onClick={onClose}><X size={20}/></button>
        </div>

        <div style={{ padding:'12px 14px', background:'rgba(245,158,11,0.08)',
          border:'1px solid rgba(245,158,11,0.25)', borderRadius:'10px', marginBottom:'20px' }}>
          <div style={{ fontWeight:600 }}>{client.username}</div>
          <div style={{ fontSize:'12px', color:'var(--text-muted)', marginTop:'2px' }}>
            Клиент будет играть в кредит — оплатит при выходе
          </div>
        </div>

        <div style={{ marginBottom:'24px' }}>
          <label style={{ fontSize:'12px', color:'var(--text-muted)', display:'block', marginBottom:'6px' }}>
            Ставка, сум/час
          </label>
          <input type="number" min="0" step="10" value={rate}
            onChange={(e) => setRate(e.target.value)} style={iStyle} autoFocus />
          <div style={{ fontSize:'11px', color:'var(--text-muted)', marginTop:'4px' }}>
            Стоимость = (минуты ÷ 60) × ставка
          </div>
        </div>

        <div style={{ display:'flex', justifyContent:'flex-end', gap:'8px' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Отмена</button>
          <button onClick={handleStart} disabled={loading}
            style={{ padding:'8px 18px', borderRadius:'8px', border:'none', cursor:'pointer',
              background:'linear-gradient(135deg,#f59e0b,#d97706)', color:'#fff',
              fontWeight:600, fontSize:'13px', fontFamily:'inherit' }}>
            {loading ? 'Запуск...' : '▶ Запустить'}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Close postpaid modal ──────────────────────────────────────────────────────
const fmtPostpaid = (mins) => {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h > 0 ? `${h}ч ${m}м` : `${m}м`;
};

const ClosePostpaidModal = ({ client, onClose, onSuccess }) => {
  const { toast } = useToast();
  const [payMethod, setPayMethod] = useState('cash');
  const [loading,   setLoading]   = useState(false);
  // BUGFIX(#3): the postpaid quote keeps accruing while the session is open, but
  // the row object is a snapshot from the last list load, so the modal showed a
  // stale (too-low) amount. Re-fetch an authoritative live quote on open — the
  // users endpoint recomputes elapsed wall-clock minutes server-side. Start from
  // the snapshot so figures show instantly, then replace with the fresh quote.
  const [quote, setQuote]   = useState({
    minutes: client.postpaid_minutes || 0,
    amount_due: client.postpaid_amount_due || 0,
    rate: client.postpaid_rate,
  });
  const [quoting, setQuoting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setQuoting(true);
    const clubId = localStorage.getItem('active_club_id');
    // noCache: avoid serving a ≤12s stale snapshot for a live, ticking quote.
    apiFetch(`/api/v1/billing/admin/users/?club=${clubId}&search=${encodeURIComponent(client.username || '')}`,
      { noCache: true })
      .then(d => {
        if (cancelled) return;
        const list = d.results || d || [];
        const fresh = list.find(c => String(c.id) === String(client.id));
        if (fresh) {
          setQuote({
            minutes: fresh.postpaid_minutes || 0,
            amount_due: fresh.postpaid_amount_due || 0,
            rate: fresh.postpaid_rate,
          });
        }
      })
      .catch(() => {}) // keep the snapshot fallback on failure
      .finally(() => { if (!cancelled) setQuoting(false); });
    return () => { cancelled = true; };
  }, [client.id, client.username]);

  const mins   = quote.minutes || 0;
  const amount = parseFloat(quote.amount_due || 0).toLocaleString('ru-RU', { minimumFractionDigits: 2 });

  const handleClose = async () => {
    setLoading(true);
    try {
      await apiFetch('/api/v1/billing/admin/postpaid/close/', {
        method: 'POST',
        body: JSON.stringify({
          user_id: String(client.id),
          payment_method: payMethod,
          club: localStorage.getItem('active_club_id'),
        }),
      });
      toast(`Сессия закрыта. Оплачено ${amount} сум`, { type: 'success' });
      onSuccess(); onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка закрытия сессии', { type: 'error' });
    } finally { setLoading(false); }
  };

  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.6)',
      display:'flex', alignItems:'center', justifyContent:'center', zIndex:900 }}
      onClick={(e) => { if (e.target===e.currentTarget) onClose(); }}>
      <div style={{ background:'var(--bg-panel)', borderRadius:'14px', padding:'24px',
        width:'420px', maxWidth:'90vw', border:'1px solid var(--border-color)' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'20px' }}>
          <h3 style={{ margin:0, display:'flex', alignItems:'center', gap:'8px' }}>
            <StopCircle size={18} color="#ef4444"/> Закрыть постоплату
          </h3>
          <button className="icon-btn" onClick={onClose}><X size={20}/></button>
        </div>

        {/* Summary */}
        <div style={{ background:'rgba(239,68,68,0.07)', border:'1px solid rgba(239,68,68,0.2)',
          borderRadius:'12px', padding:'16px', marginBottom:'20px', textAlign:'center' }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:'6px',
            fontSize:'13px', color:'var(--text-muted)', marginBottom:'8px' }}>
            <Timer size={14}/> {client.username} — сыграл
          </div>
          <div style={{ fontSize:'28px', fontWeight:700, color:'var(--text-main)', marginBottom:'4px' }}>
            {fmtPostpaid(mins)}
          </div>
          <div style={{ fontSize:'22px', fontWeight:700, color:'#f59e0b' }}>
            {amount} сум {quoting && <span style={{ fontSize:'11px', fontWeight:400, color:'var(--text-muted)' }}>(обновление…)</span>}
          </div>
          <div style={{ fontSize:'11px', color:'var(--text-muted)', marginTop:'4px' }}>
            {quote.rate} сум/ч × {mins} мин
          </div>
        </div>

        {/* Payment method */}
        <div style={{ marginBottom:'24px' }}>
          <label style={{ fontSize:'12px', color:'var(--text-muted)', display:'block', marginBottom:'8px' }}>
            Способ оплаты
          </label>
          <div style={{ display:'flex', gap:'6px' }}>
            {[{v:'cash',l:'💵 Наличные'},{v:'card',l:'💳 Карта'},{v:'transfer',l:'📲 Перевод'}].map(m => (
              <button key={m.v} type="button" onClick={() => setPayMethod(m.v)}
                style={{ flex:1, padding:'8px', borderRadius:'8px', fontSize:'12px',
                  cursor:'pointer', fontFamily:'inherit',
                  background: payMethod===m.v ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.04)',
                  border:`1px solid ${payMethod===m.v ? '#10b981' : 'var(--border-color)'}`,
                  color: payMethod===m.v ? '#10b981' : 'var(--text-muted)' }}>
                {m.l}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display:'flex', justifyContent:'flex-end', gap:'8px' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Отмена</button>
          <button onClick={handleClose} disabled={loading}
            style={{ padding:'8px 18px', borderRadius:'8px', border:'none', cursor:'pointer',
              background:'linear-gradient(135deg,#ef4444,#dc2626)', color:'#fff',
              fontWeight:600, fontSize:'13px', fontFamily:'inherit' }}>
            {loading ? 'Закрытие...' : `■ Закрыть и взять ${amount} сум`}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Client group modal ────────────────────────────────────────────────────────
const ClientGroupModal = ({ group, clubId, onClose, onSuccess }) => {
  const { toast } = useToast();
  const isEdit = !!group;
  const [name, setName]         = useState(group?.name || '');
  const [discount, setDiscount] = useState(group?.percent_discount ?? 0);
  const [loading, setLoading]   = useState(false);

  const save = async () => {
    if (!name.trim()) { toast('Введите название', { type: 'warning' }); return; }
    setLoading(true);
    try {
      if (isEdit) {
        await apiFetch(`/api/v1/clubs/client-groups/${group.id}/`, {
          method: 'PATCH', body: JSON.stringify({ name: name.trim(), percent_discount: Number(discount) }),
        });
      } else {
        await apiFetch('/api/v1/clubs/client-groups/', {
          method: 'POST', body: JSON.stringify({ name: name.trim(), percent_discount: Number(discount), club: clubId }),
        });
      }
      toast(isEdit ? 'Группа обновлена' : 'Группа создана', { type: 'success' });
      onSuccess(); onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка', { type: 'error' });
    } finally { setLoading(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 950,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: '14px', padding: '24px',
        width: '380px', maxWidth: '90vw', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ margin: 0 }}>{isEdit ? 'Группа клиентов' : 'Новая группа клиентов'}</h3>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <div style={{ flex: 2 }}>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Название</label>
            <input value={name} onChange={e => setName(e.target.value)} maxLength={16}
              placeholder="Сотрудники" style={iStyle} autoFocus />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Скидка, %</label>
            <input type="number" min="0" max="100" value={discount}
              onChange={e => setDiscount(e.target.value)} style={iStyle} />
          </div>
        </div>
        <button className="btn btn-primary" onClick={save} disabled={loading}
          style={{ width: '100%', padding: '11px' }}>
          {loading ? 'Сохранение…' : isEdit ? 'Сохранить' : 'Создать'}
        </button>
      </div>
    </div>
  );
};

// ── Rich client profile modal (3 tabs) ─────────────────────────────────────────
const ClientProfileModal = ({ client, clubId, groups, onClose, onSuccess, onDeposit }) => {
  const { toast } = useToast();
  const [tab, setTab]           = useState('profile'); // profile | comments | subs
  const [payTab, setPayTab]     = useState('payments'); // payments | bonuses | transfers
  const [discount, setDiscount] = useState(client.personal_discount || 0);
  const [blocked, setBlocked]   = useState(client.is_blocked || false);
  const [groupId, setGroupId]   = useState(client.group_id || '');
  const [editingDisc, setEditingDisc] = useState(false);
  const [payments, setPayments] = useState([]);
  const [page, setPage]         = useState(1);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const PAGE = 8;

  // Load payments + comments
  useEffect(() => {
    apiFetch(`/api/v1/billing/admin/payments/?user_id=${client.id}&club=${clubId}`)
      .then(d => setPayments(d.results || d || [])).catch(() => {});
    apiFetch(`/api/v1/clubs/clients/${client.id}/comments/?club=${clubId}`)
      .then(d => setComments(d || [])).catch(() => {});
  }, [client.id, clubId]);

  const saveProfile = async (patch) => {
    try {
      // The backend clamps personal_discount to 0..100 and returns the stored
      // value — return it so callers can resync their input to the saved figure.
      const res = await apiFetch(`/api/v1/billing/admin/users/${client.id}/profile/?club=${clubId}`, {
        method: 'PATCH', body: JSON.stringify({ ...patch, club: clubId }),
      });
      onSuccess();
      return res;
    } catch (e) { toast('Ошибка сохранения', { type: 'error' }); }
  };

  const assignGroup = async (gid) => {
    setGroupId(gid);
    try {
      await apiFetch(`/api/v1/clubs/clients/${client.id}/group/?club=${clubId}`, {
        method: 'PATCH', body: JSON.stringify({ group: gid || null, club: clubId }),
      });
      onSuccess();
    } catch { toast('Ошибка', { type: 'error' }); }
  };

  const toggleBlock = async () => {
    const nv = !blocked; setBlocked(nv);
    await saveProfile({ is_blocked: nv });
  };

  const addComment = async () => {
    if (!newComment.trim()) return;
    try {
      const c = await apiFetch(`/api/v1/clubs/clients/${client.id}/comments/?club=${clubId}`, {
        method: 'POST', body: JSON.stringify({ text: newComment.trim(), club: clubId }),
      });
      setComments(prev => [c, ...prev]); setNewComment('');
    } catch { toast('Ошибка', { type: 'error' }); }
  };
  const toggleImportant = async (c) => {
    try {
      await apiFetch(`/api/v1/clubs/client-comments/${c.id}/`, {
        method: 'PATCH', body: JSON.stringify({ is_important: !c.is_important }),
      });
      setComments(prev => prev.map(x => x.id === c.id ? { ...x, is_important: !x.is_important } : x));
    } catch {}
  };
  const delComment = async (c) => {
    try {
      await apiFetch(`/api/v1/clubs/client-comments/${c.id}/`, { method: 'DELETE' });
      setComments(prev => prev.filter(x => x.id !== c.id));
    } catch {}
  };

  const deposit = Number(client.deposit_money || 0);
  const bonus = Number(client.bonus_balance || 0);
  const totalPages = Math.ceil(payments.length / PAGE) || 1;
  const pagePayments = payments.slice((page - 1) * PAGE, page * PAGE);

  const payCategory = (p) => {
    const n = p.note || '';
    if (n.includes('[POS]')) return 'Покупка в магазине';
    if (n.includes('[POSTPAID]')) return 'Постоплата';
    if (n.includes('[CLIENT]') || p.minutes_added > 0) return 'Покупка тарифов';
    return 'Пополнение депозита';
  };
  const methodLabel = (m) => ({ cash: '💵 Наличные', card: '💳 Карта', deposit: '🏦 Депозит', transfer: '📲 Перевод' }[m] || m);

  const fld = { width: '100%', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
    borderRadius: '8px', padding: '8px 10px', color: 'var(--text-light)', fontSize: '13px', fontFamily: 'inherit', boxSizing: 'border-box' };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 900,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: '16px', width: '900px', maxWidth: '95vw',
        height: '600px', maxHeight: '90vh', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Top tabs */}
        <div style={{ display: 'flex', alignItems: 'center', padding: '14px 20px', borderBottom: '1px solid var(--border-color)', gap: '4px' }}>
          {[['profile', 'Профиль клиента'], ['comments', 'Комментарии'], ['subs', 'Абонементы']].map(([id, l]) => (
            <button key={id} onClick={() => setTab(id)}
              style={{ padding: '7px 14px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer', border: 'none', fontFamily: 'inherit',
                background: tab === id ? 'var(--accent)' : 'transparent', color: tab === id ? '#fff' : 'var(--text-muted)', fontWeight: 500 }}>
              {l}
            </button>
          ))}
          <div style={{ flex: 1 }} />
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>

        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left sidebar */}
          <div style={{ width: '280px', flexShrink: 0, borderRight: '1px solid var(--border-color)',
            padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '44px', height: '44px', borderRadius: '50%',
                background: 'linear-gradient(135deg,#6366f1,#a855f7)', display: 'flex', alignItems: 'center',
                justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: '18px' }}>
                {(client.username || '?')[0].toUpperCase()}
              </div>
              <div style={{ overflow: 'hidden' }}>
                <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{client.username}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{client.phone || '—'}</div>
              </div>
            </div>

            <button className="btn btn-primary" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
              onClick={() => { onClose(); onDeposit(client); }}>
              <CreditCard size={14} /> Пополнить депозит
            </button>

            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', padding: '3px 10px', borderRadius: '999px',
                background: blocked ? 'rgba(239,68,68,0.12)' : 'rgba(99,102,241,0.12)',
                color: blocked ? '#ef4444' : '#818cf8' }}>{blocked ? 'Заблокирован' : 'Клиент'}</span>
              {client.effective_discount > 0 && (
                <span style={{ fontSize: '11px', padding: '3px 10px', borderRadius: '999px',
                  background: 'rgba(139,92,246,0.12)', color: '#8b5cf6' }}>{client.effective_discount}%</span>
              )}
            </div>

            {/* Editable fields */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid var(--border-row)', paddingTop: '12px' }}>
              <div>
                <label style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '3px' }}>
                  <CreditCard size={11} /> Депозит, сум</label>
                <input value={deposit.toLocaleString('ru-RU')} disabled style={{ ...fld, opacity: 0.7 }} />
              </div>
              <div>
                <label style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '3px' }}>
                  <Percent size={11} /> Бонусы</label>
                <input value={bonus.toLocaleString('ru-RU')} disabled style={{ ...fld, opacity: 0.7 }} />
              </div>
              <div>
                <label style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '3px' }}>
                  <Percent size={11} /> Персональная скидка, %</label>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <input type="number" min="0" max="100" value={discount} disabled={!editingDisc}
                    onChange={e => setDiscount(e.target.value)} style={{ ...fld, opacity: editingDisc ? 1 : 0.7 }} />
                  <button className="icon-btn" style={{ flexShrink: 0 }}
                    onClick={async () => {
                      if (editingDisc) {
                        // BUGFIX(#3): resync the input to the SAVED (server-clamped 0..100)
                        // value — previously e.g. "250" stayed in the box while the backend
                        // stored 100, so the UI lied about the effective discount.
                        const res = await saveProfile({ personal_discount: Number(discount) });
                        if (res && res.personal_discount !== undefined) setDiscount(res.personal_discount);
                      }
                      setEditingDisc(v => !v);
                    }}>
                    {editingDisc ? <span style={{ color: '#10b981' }}>✓</span> : <Edit2 size={13} />}
                  </button>
                </div>
              </div>
              {/* Group */}
              <div>
                <label style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'block', marginBottom: '3px' }}>Группа</label>
                <select value={groupId} onChange={e => assignGroup(e.target.value)} style={fld}>
                  <option value="">Без группы</option>
                  {groups.map(g => <option key={g.id} value={g.id}>{g.name} ({g.percent_discount}%)</option>)}
                </select>
              </div>
            </div>

            {/* Details */}
            <div style={{ borderTop: '1px solid var(--border-row)', paddingTop: '12px', fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '12px' }}>Подробнее о клиенте</div>
              <div>📅 Регистрация: {client.registered_at ? new Date(client.registered_at).toLocaleDateString('ru-RU') : '—'}</div>
              <div>⏱ Остаток: {client.formatted_time || '0ч 0м'}</div>
              {client.last_visit_at && <div>🕓 Был: {new Date(client.last_visit_at).toLocaleDateString('ru-RU')}</div>}
            </div>

            {/* Block toggle */}
            <div onClick={toggleBlock} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer',
              padding: '10px', borderRadius: '10px', borderTop: '1px solid var(--border-row)', marginTop: 'auto' }}>
              <ShieldOff size={14} color={blocked ? '#ef4444' : 'var(--text-muted)'} />
              <span style={{ fontSize: '13px', flex: 1, color: blocked ? '#ef4444' : 'var(--text-main)' }}>Заблокировать</span>
              <div style={{ width: '36px', height: '20px', borderRadius: '999px', position: 'relative',
                background: blocked ? '#ef4444' : 'var(--border-color)', transition: 'background 0.2s' }}>
                <div style={{ width: '16px', height: '16px', borderRadius: '50%', background: '#fff', position: 'absolute',
                  top: '2px', left: blocked ? '18px' : '2px', transition: 'left 0.2s' }} />
              </div>
            </div>
          </div>

          {/* Right content */}
          <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            {tab === 'profile' && (
              <>
                {/* Payment sub-tabs */}
                <div style={{ display: 'flex', gap: '4px', marginBottom: '16px' }}>
                  {[['payments', 'Платежи'], ['bonuses', 'Бонусы'], ['transfers', 'Переводы']].map(([id, l]) => (
                    <button key={id} onClick={() => setPayTab(id)}
                      style={{ padding: '6px 14px', borderRadius: '8px', fontSize: '12px', cursor: 'pointer', border: 'none', fontFamily: 'inherit',
                        background: payTab === id ? 'var(--hover-overlay)' : 'transparent', color: payTab === id ? 'var(--text-main)' : 'var(--text-muted)', fontWeight: 500 }}>
                      {l}
                    </button>
                  ))}
                </div>
                {payTab === 'payments' && (
                  payments.length === 0 ? (
                    <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>Платежей нет</div>
                  ) : (
                    <>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                            {['Дата', 'Оператор', 'Категория', 'Оплата', 'Итого'].map(c => (
                              <th key={c} style={{ padding: '8px 10px', textAlign: c === 'Итого' ? 'right' : 'left', fontSize: '10px',
                                color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>{c}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {pagePayments.map(p => (
                            <tr key={p.id} style={{ borderBottom: '1px solid var(--border-row)' }}>
                              <td style={{ padding: '8px 10px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                                {new Date(p.created_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })}</td>
                              <td style={{ padding: '8px 10px', color: 'var(--text-muted)' }}>{p.admin_username || '—'}</td>
                              <td style={{ padding: '8px 10px', color: '#3b82f6' }}>{payCategory(p)}</td>
                              <td style={{ padding: '8px 10px', fontSize: '11px' }}>{methodLabel(p.payment_method)}</td>
                              <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600,
                                color: (p.note || '').includes('[REFUNDED]') ? '#ef4444' : 'var(--text-main)' }}>
                                {Number(p.amount_paid).toLocaleString('ru-RU')} сум</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {totalPages > 1 && (
                        <div style={{ display: 'flex', justifyContent: 'center', gap: '4px', marginTop: '16px' }}>
                          {Array.from({ length: totalPages }, (_, i) => i + 1).slice(0, 10).map(p => (
                            <button key={p} onClick={() => setPage(p)}
                              style={{ width: '28px', height: '28px', borderRadius: '6px', cursor: 'pointer', border: 'none', fontFamily: 'inherit', fontSize: '12px',
                                background: page === p ? 'var(--accent)' : 'var(--hover-overlay)', color: page === p ? '#fff' : 'var(--text-muted)' }}>{p}</button>
                          ))}
                        </div>
                      )}
                    </>
                  )
                )}
                {payTab === 'bonuses' && <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>Текущий бонусный баланс: {bonus.toLocaleString('ru-RU')} сум</div>}
                {payTab === 'transfers' && <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>Переводов нет</div>}
              </>
            )}

            {tab === 'comments' && (
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {comments.length === 0 ? (
                    <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>Комментариев нет</div>
                  ) : comments.map(c => (
                    <div key={c.id} style={{ padding: '12px 14px', borderRadius: '10px',
                      background: c.is_important ? 'rgba(245,158,11,0.08)' : 'var(--hover-overlay)',
                      border: `1px solid ${c.is_important ? 'rgba(245,158,11,0.3)' : 'var(--border-color)'}` }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          {c.author} · {new Date(c.created_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button className="icon-btn" title="Пометить важным" onClick={() => toggleImportant(c)}
                            style={{ width: '24px', height: '24px', color: c.is_important ? '#f59e0b' : 'var(--text-muted)' }}>!</button>
                          <button className="icon-btn" title="Удалить" onClick={() => delComment(c)}
                            style={{ width: '24px', height: '24px', color: '#ef4444' }}>✕</button>
                        </div>
                      </div>
                      <div style={{ fontSize: '13px' }}>{c.text}</div>
                    </div>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
                  <input value={newComment} onChange={e => setNewComment(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && addComment()}
                    placeholder="Комментарий" style={iStyle} />
                  <button className="btn btn-primary" onClick={addComment}>➤</button>
                </div>
              </div>
            )}

            {tab === 'subs' && (
              <div style={{ padding: '50px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                У клиента нет активных абонементов
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────
const Clients = () => {
  const { toast } = useToast();
  const [clients, setClients]         = useState([]);
  const [groups, setGroups]           = useState([]);
  const [loading, setLoading]         = useState(true);
  const [search, setSearch]           = useState('');
  const [tab, setTab]                 = useState('clients'); // clients | groups
  const [groupFilter, setGroupFilter] = useState('');
  const [sort, setSort]               = useState({ key: null, dir: 1 });
  const [depositClient, setDepositClient]     = useState(null);
  const [profileClient, setProfileClient]     = useState(null);
  const [showAddModal, setShowAddModal]       = useState(false);
  const [groupModal, setGroupModal]           = useState(null); // {} new, group edit
  const [postpaidStart, setPostpaidStart]     = useState(null);
  const [postpaidClose, setPostpaidClose]     = useState(null);

  const clubId = localStorage.getItem('active_club_id');

  const load = useCallback(async () => {
    if (!clubId) { setLoading(false); return; }
    setLoading(true);
    try {
      const [cJson, gJson] = await Promise.all([
        // BUGFIX(#3): default DRF pagination caps the client list at 200 — clubs
        // with more clients silently lost the rest (and totals/CSV were wrong).
        // Raise the limit so the full roster loads. NOTE: this is a generous
        // single-page cap, not true pagination — very large clubs (>2000) would
        // still need a backend page-through, but 2000 covers realistic clubs.
        apiFetch(`/api/v1/billing/admin/users/?club=${clubId}&limit=2000`),
        apiFetch(`/api/v1/clubs/client-groups/?club=${clubId}`).catch(() => []),
      ]);
      setClients(cJson.results || cJson || []);
      setGroups(gJson || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [clubId]);

  useEffect(() => { load(); }, [load]);

  const deleteGroup = async (g) => {
    if (!window.confirm(`Удалить группу «${g.name}»?`)) return;
    try { await apiFetch(`/api/v1/clubs/client-groups/${g.id}/`, { method: 'DELETE' }); toast('Группа удалена', { type: 'success' }); load(); }
    catch { toast('Ошибка', { type: 'error' }); }
  };

  let filtered = clients.filter(c => {
    const q = search.toLowerCase();
    const matchSearch = !q || (c.username || '').toLowerCase().includes(q)
      || (c.phone || '').includes(search) || (c.email || '').toLowerCase().includes(q);
    const matchGroup = !groupFilter || String(c.group_id) === String(groupFilter);
    return matchSearch && matchGroup;
  });
  if (sort.key) {
    filtered = [...filtered].sort((a, b) => {
      const get = (x) => {
        if (sort.key === 'deposit') return Number(x.deposit_money || 0);
        if (sort.key === 'discount') return x.effective_discount || x.personal_discount || 0;
        if (sort.key === 'last') return x.last_visit_at ? new Date(x.last_visit_at).getTime() : 0;
        if (sort.key === 'reg') return x.registered_at ? new Date(x.registered_at).getTime() : 0;
        return (x[sort.key] || '').toString();
      };
      const av = get(a), bv = get(b);
      if (typeof av === 'number') return (av - bv) * sort.dir;
      return av.localeCompare(bv) * sort.dir;
    });
  }

  const totalDeposit = clients.reduce((s, c) => s + Number(c.deposit_money || 0), 0);

  const exportCSV = () => {
    const headers = ['Никнейм', 'Телефон', 'Скидка', 'Группа', 'Депозит', 'Бонусы', 'Статус', 'Регистрация'];
    const lines = [headers.join(';'), ...filtered.map(c => [
      c.username, c.phone || '', `${c.effective_discount || 0}%`, c.group_name || '',
      Number(c.deposit_money || 0).toFixed(2), Number(c.bonus_balance || 0).toFixed(2),
      c.is_blocked ? 'Заблокирован' : 'Активен',
      c.registered_at ? new Date(c.registered_at).toLocaleDateString('ru-RU') : '',
    ].join(';'))];
    const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `clients_${new Date().toISOString().slice(0,10)}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const Th = ({ label, sortKey }) => (
    <th onClick={() => sortKey && setSort(s => ({ key: sortKey, dir: s.key === sortKey ? -s.dir : 1 }))}
      style={{ padding: '12px 14px', textAlign: 'left', fontWeight: 500, fontSize: '11px',
        color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px',
        whiteSpace: 'nowrap', cursor: sortKey ? 'pointer' : 'default', userSelect: 'none' }}>
      {label} {sortKey && (sort.key === sortKey ? (sort.dir === 1 ? '↑' : '↓') : '↕')}
    </th>
  );

  return (
    <div style={{ padding: '0 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Users size={20} /> Клиенты
        </h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn btn-secondary" onClick={exportCSV}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
            <Download size={13} /> Экспорт в CSV
          </button>
          {tab === 'clients' ? (
            <button className="btn btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              onClick={() => setShowAddModal(true)}>
              <UserPlus size={14} /> Создать клиента
            </button>
          ) : (
            <button className="btn btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              onClick={() => setGroupModal({})}>
              <Plus size={14} /> Создать группу
            </button>
          )}
        </div>
      </div>

      {/* Tabs + filters */}
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '2px', padding: '2px', background: 'var(--bg-panel)',
          borderRadius: '9px', border: '1px solid var(--border-color)' }}>
          {[['clients', `Клиенты ${clients.length}`], ['groups', `Группы ${groups.length}`]].map(([id, l]) => (
            <button key={id} onClick={() => setTab(id)}
              style={{ padding: '6px 14px', borderRadius: '7px', fontSize: '12px', cursor: 'pointer', border: 'none', fontFamily: 'inherit', fontWeight: 500,
                background: tab === id ? 'var(--accent)' : 'transparent', color: tab === id ? '#fff' : 'var(--text-muted)' }}>
              {l}
            </button>
          ))}
        </div>
        {tab === 'clients' && (
          <>
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input type="text" placeholder="Найти клиента" value={search} onChange={(e) => setSearch(e.target.value)}
                style={{ background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: '8px',
                  padding: '8px 12px 8px 32px', color: 'var(--text-light)', fontSize: '13px', width: '200px' }} />
            </div>
            <select value={groupFilter} onChange={e => setGroupFilter(e.target.value)}
              style={{ background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: '8px',
                padding: '8px 12px', color: 'var(--text-light)', fontSize: '13px', fontFamily: 'inherit' }}>
              <option value="">Все группы</option>
              {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              На депозите: <strong style={{ color: '#f59e0b' }}>{totalDeposit.toLocaleString('ru-RU')} сум</strong>
            </span>
            <button className="btn btn-secondary" onClick={load} style={{ marginLeft: 'auto' }}><RefreshCw size={14} /></button>
          </>
        )}
      </div>

      {/* GROUPS TAB */}
      {tab === 'groups' && (
        <div style={{ background: 'var(--bg-panel)', borderRadius: '12px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
          {groups.length === 0 ? (
            <div style={{ padding: '50px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Групп пока нет. Нажмите «Создать группу».
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead><tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                {['Название', 'Скидка', 'Клиентов', ''].map(l => (
                  <th key={l} style={{ padding: '12px 14px', textAlign: l === '' ? 'right' : 'left', fontSize: '11px',
                    color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase' }}>{l}</th>
                ))}
              </tr></thead>
              <tbody>
                {groups.map(g => (
                  <tr key={g.id} style={{ borderBottom: '1px solid var(--border-row)' }}>
                    <td style={{ padding: '12px 14px', fontWeight: 600 }}>{g.name}</td>
                    <td style={{ padding: '12px 14px', color: '#8b5cf6', fontWeight: 600 }}>{g.percent_discount}%</td>
                    <td style={{ padding: '12px 14px', color: 'var(--text-muted)' }}>{g.members_count} чел.</td>
                    <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                      <button className="icon-btn" onClick={() => setGroupModal(g)} style={{ marginRight: '4px' }}><Edit2 size={14} /></button>
                      <button className="icon-btn" onClick={() => deleteGroup(g)} style={{ color: '#ef4444' }}><X size={14} /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* CLIENTS TAB */}
      {tab === 'clients' && (
      <div style={{ background: 'var(--bg-panel)', borderRadius: '12px',
        border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <Th label="Никнейм" sortKey="username" />
              <Th label="Телефон" sortKey="phone" />
              <Th label="Посл. посещение" sortKey="last" />
              <Th label="Скидка" sortKey="discount" />
              <Th label="Группа" />
              <Th label="Депозит" sortKey="deposit" />
              <Th label="Статус" />
              <Th label="Регистрация" sortKey="reg" />
              <th style={{ padding: '12px 14px', textAlign: 'right', fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={9} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Загрузка…</td></tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr><td colSpan={9} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                {search ? 'Клиенты не найдены' : 'Клиентов пока нет'}
              </td></tr>
            )}
            {filtered.map(c => {
              const mins = c.minutes_remaining || 0;
              // Online = currently LOGGED IN (is_active_session). Was OR'd with is_active,
              // which means "has an active session/time on the profile", not "logged in" —
              // so a client who logged out (is_active_session cleared) still showed «Активен».
              const isOnline = c.is_active_session || false;
              const deposit = Number(c.deposit_money || 0);
              const discount = c.personal_discount || 0;
              return (
                <tr key={c.id} style={{
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  background: c.is_blocked
                    ? 'rgba(239,68,68,0.04)'
                    : isOnline ? 'rgba(16,185,129,0.04)' : 'transparent',
                }}>
                  <td style={{ padding: '12px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{ width: '30px', height: '30px', borderRadius: '50%', flexShrink: 0,
                        background: c.is_blocked
                          ? 'linear-gradient(135deg,#ef4444,#dc2626)'
                          : 'linear-gradient(135deg,#6366f1,#a855f7)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        color: '#fff', fontWeight: 700, fontSize: '13px' }}>
                        {(c.username || '?')[0].toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontWeight: 500, display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {c.username}
                          {c.is_blocked && (
                            <span style={{ fontSize: '10px', background: 'rgba(239,68,68,0.15)',
                              color: '#ef4444', borderRadius: '4px', padding: '1px 5px' }}>
                              БАН
                            </span>
                          )}
                        </div>
                        {c.full_name && c.full_name !== c.username && (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{c.full_name}</div>
                        )}
                        {c.comment && (
                          <div style={{ fontSize: '10px', color: '#f59e0b', fontStyle: 'italic',
                            maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            💬 {c.comment}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '12px 14px', color: 'var(--text-muted)', fontSize: '12px' }}>
                    {c.phone || '—'}
                  </td>
                  {/* Посл. посещение */}
                  <td style={{ padding: '12px 14px', color: 'var(--text-muted)', fontSize: '12px' }}>
                    {c.last_visit_at ? new Date(c.last_visit_at).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' }) : '—'}
                  </td>
                  {/* Скидка */}
                  <td style={{ padding: '12px 14px' }}>
                    {(c.effective_discount || discount) > 0 ? (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px',
                        color: '#8b5cf6', fontWeight: 600, fontSize: '12px' }}>
                        <Percent size={11} />{c.effective_discount || discount}%
                      </span>
                    ) : <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>0%</span>}
                  </td>
                  {/* Группа */}
                  <td style={{ padding: '12px 14px', fontSize: '12px' }}>
                    {c.group_name ? (
                      <span style={{ padding: '3px 9px', borderRadius: '999px', fontSize: '11px',
                        background: 'rgba(99,102,241,0.12)', color: '#818cf8' }}>{c.group_name}</span>
                    ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                  </td>
                  {/* Депозит + бонусы */}
                  <td style={{ padding: '12px 14px' }}>
                    <span style={{ fontWeight: 600, color: deposit > 0 ? '#f59e0b' : 'var(--text-muted)' }}>
                      {deposit.toLocaleString('ru-RU')} сум
                    </span>
                    {Number(c.bonus_balance || 0) > 0 && (
                      <span style={{ marginLeft: '6px', fontSize: '11px', color: '#ec4899' }}>
                        +{Number(c.bonus_balance).toLocaleString('ru-RU')} б.
                      </span>
                    )}
                  </td>
                  {/* Статус */}
                  <td style={{ padding: '12px 14px' }}>
                    {c.is_blocked ? (
                      <span style={{ padding: '3px 10px', borderRadius: '999px', fontSize: '11px',
                        background: 'rgba(239,68,68,0.12)', color: '#ef4444', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <ShieldOff size={10} /> Заблокирован
                      </span>
                    ) : c.session_mode === 'postpaid' ? (
                      <span style={{ padding: '3px 10px', borderRadius: '999px', fontSize: '11px',
                        background: 'rgba(245,158,11,0.15)', color: '#f59e0b', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Timer size={10} /> Постоплата
                      </span>
                    ) : isOnline ? (
                      <span style={{ padding: '3px 10px', borderRadius: '999px', fontSize: '11px',
                        background: 'rgba(16,185,129,0.12)', color: '#10b981', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Wifi size={10} /> Активен
                      </span>
                    ) : (
                      <span style={{ padding: '3px 10px', borderRadius: '999px', fontSize: '11px',
                        background: 'rgba(255,255,255,0.04)', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <WifiOff size={10} /> Офлайн
                      </span>
                    )}
                  </td>
                  {/* Регистрация */}
                  <td style={{ padding: '12px 14px', color: 'var(--text-muted)', fontSize: '12px' }}>
                    {c.registered_at ? new Date(c.registered_at).toLocaleDateString('ru-RU') : '—'}
                  </td>
                  <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                    {c.session_mode === 'postpaid' ? (
                      /* Postpaid active — show Close button */
                      <button title="Закрыть постоплату и взять оплату"
                        onClick={() => setPostpaidClose(c)}
                        style={{ display:'inline-flex', alignItems:'center', gap:'5px',
                          padding:'5px 12px', borderRadius:'7px', border:'none',
                          background:'linear-gradient(135deg,#ef4444,#dc2626)',
                          color:'#fff', fontSize:'12px', fontWeight:600,
                          cursor:'pointer', fontFamily:'inherit', marginRight:'4px' }}>
                        <StopCircle size={13}/> Закрыть
                      </button>
                    ) : (
                      /* Prepaid — show Start Postpaid button */
                      <button className="icon-btn" title="Запустить постоплату"
                        onClick={() => setPostpaidStart(c)} style={{ marginRight: '4px' }}>
                        <PlayCircle size={14} color="#f59e0b"/>
                      </button>
                    )}
                    <button className="icon-btn" title="Профиль клиента"
                      onClick={() => setProfileClient(c)} style={{ marginRight: '4px' }}>
                      <Edit2 size={14} />
                    </button>
                    <button className="icon-btn" title="Пополнить депозит"
                      onClick={() => setDepositClient(c)}>
                      <CreditCard size={14} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      )}

      {showAddModal && (
        <AddClientModal clubId={clubId}
          onClose={() => setShowAddModal(false)}
          onSuccess={load} />
      )}
      {groupModal && (
        <ClientGroupModal group={groupModal.id ? groupModal : null} clubId={clubId}
          onClose={() => setGroupModal(null)} onSuccess={load} />
      )}
      {postpaidStart && (
        <PostpaidStartModal client={postpaidStart}
          onClose={() => setPostpaidStart(null)}
          onSuccess={load} />
      )}
      {postpaidClose && (
        <ClosePostpaidModal client={postpaidClose}
          onClose={() => setPostpaidClose(null)}
          onSuccess={load} />
      )}
      {depositClient && (
        <DepositModal client={depositClient}
          onClose={() => setDepositClient(null)}
          onSuccess={load} />
      )}
      {profileClient && (
        <ClientProfileModal client={profileClient} clubId={clubId} groups={groups}
          onClose={() => setProfileClient(null)}
          onSuccess={load}
          onDeposit={(c) => setDepositClient(c)} />
      )}
    </div>
  );
};

export default Clients;
