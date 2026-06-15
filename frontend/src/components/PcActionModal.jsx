import { useState, useEffect } from 'react';
import { X, Wallet, Calendar, Bell, Zap, Lock, Ban, ArrowLeftRight, Settings, MonitorOff } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from './Toast';

// Universal modal for PC context-menu actions.
const MODE_META = {
  topup:    { title: 'Пополнение депозита',   icon: Wallet,        accent: '#10b981' },
  booking:  { title: 'Создать бронь',         icon: Calendar,      accent: '#6366f1' },
  notify:   { title: 'Отправить уведомление', icon: Bell,          accent: '#3b82f6' },
  power:    { title: 'Электропитание',        icon: Zap,           accent: '#f59e0b' },
  postpay:  { title: 'Запустить постоплату',  icon: Lock,          accent: '#f59e0b' },
  penalty:  { title: 'Выписать штраф',        icon: Ban,           accent: '#ef4444' },
  transfer: { title: 'Смена места',           icon: ArrowLeftRight, accent: '#8b5cf6' },
  control:  { title: 'Управление ПК',         icon: Settings,      accent: '#6366f1' },
  shell:    { title: 'Шелл',                  icon: MonitorOff,    accent: '#3b82f6' },
};

const PcActionModal = ({ mode, pc, isOpen, onClose, onDone }) => {
  const meta = MODE_META[mode];
  const { toast } = useToast();
  const clubId = localStorage.getItem('active_club_id');

  // Shared form state
  const [busy, setBusy] = useState(false);
  // topup
  const [users, setUsers] = useState([]);
  const [userId, setUserId] = useState('');
  const [amount, setAmount] = useState('');
  const [minutes, setMinutes] = useState('1');
  const [method, setMethod] = useState('cash');
  const [note, setNote] = useState('');
  // booking
  const fmtLocal = (d) => {
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  const [guestName, setGuestName] = useState('');
  const [guestPhone, setGuestPhone] = useState('');
  const [guestPostpaid, setGuestPostpaid] = useState(false); // walk-in postpaid, no account
  const [fromAt, setFromAt] = useState('');
  const [toAt, setToAt] = useState('');
  // notify
  const [notifyText, setNotifyText] = useState('');
  // power
  const [powerCmd, setPowerCmd] = useState('reboot');
  // postpay
  const [rate, setRate] = useState('100');
  // penalty
  const [penaltyReason, setPenaltyReason] = useState('');
  // transfer
  const [computers, setComputers] = useState([]);
  const [targetPc, setTargetPc] = useState('');
  // control / shell — values MUST be canonical CommandType members the backend
  // ChoiceField accepts AND the shell switch handles (was inventing tokens → 400).
  const [ctrlCmd, setCtrlCmd] = useState('kill_games');
  const [shellCmd, setShellCmd] = useState('lock');

  useEffect(() => {
    if (!isOpen) return;
    // reset form when reopening
    setBusy(false);
    setAmount(''); setMinutes('1'); setMethod('cash'); setNote(''); setUserId('');
    setGuestName(''); setGuestPhone('');
    setNotifyText('');
    setPowerCmd('reboot');
    setRate('100'); setPenaltyReason(''); setTargetPc('');
    setCtrlCmd('kill_games'); setShellCmd('lock');
    const now = new Date();
    const later = new Date(now.getTime() + 60 * 60 * 1000);
    setFromAt(fmtLocal(now));
    setToAt(fmtLocal(later));

    // Load clients for actions that target a specific client
    if (['topup', 'postpay', 'penalty'].includes(mode)) {
      const clubId2 = localStorage.getItem('active_club_id');
      apiFetch(`/api/v1/billing/admin/users/?club=${clubId2}`)
        .then(data => {
          const list = data.results || data || [];
          setUsers(list);
          const active = pc?.activeUser ? list.find(u => u.username === pc.activeUser) : null;
          if (active) setUserId(String(active.id));
        })
        .catch(() => setUsers([]));
    }
    // Load other computers for transfer
    if (mode === 'transfer') {
      const clubId2 = localStorage.getItem('active_club_id');
      apiFetch(`/api/v1/computers/?club=${clubId2}`)
        .then(data => {
          const list = (data.results || data || []).filter(c => String(c.id) !== String(pc?.id));
          setComputers(list);
        })
        .catch(() => setComputers([]));
    }
  }, [isOpen, mode, pc]);

  if (!isOpen || !meta) return null;
  const Icon = meta.icon;

  const submit = async () => {
    setBusy(true);
    try {
      if (mode === 'topup') {
        if (!userId) { toast('Выберите клиента', { type: 'warning' }); setBusy(false); return; }
        if (!amount || Number(amount) <= 0) { toast('Введите сумму', { type: 'warning' }); setBusy(false); return; }
        const res = await apiFetch('/api/v1/billing/admin/topup/', {
          method: 'POST',
          body: JSON.stringify({
            user_id: String(userId),
            amount_paid: Number(amount),
            minutes: Math.max(1, Number(minutes) || 1),
            payment_method: method === 'card' ? 'card' : 'cash',
            note,
          }),
        });
        toast(`Пополнено ${res.amount_paid || amount} сум`, { type: 'success' });
      } else if (mode === 'booking') {
        if (!fromAt || !toAt) { toast('Укажите время', { type: 'warning' }); setBusy(false); return; }
        await apiFetch('/api/v1/bookings/', {
          method: 'POST',
          body: JSON.stringify({
            club: clubId ? Number(clubId) : undefined,
            hosts: [Number(pc.id)],
            guest_name: guestName,
            guest_phone: guestPhone,
            from_at: new Date(fromAt).toISOString(),
            to_at: new Date(toAt).toISOString(),
            comment: note,
            hard_booking: false,
          }),
        });
        toast(`Бронь на ПК-${pc.alias} создана`, { type: 'success' });
      } else if (mode === 'notify') {
        if (!notifyText.trim()) { toast('Введите текст', { type: 'warning' }); setBusy(false); return; }
        await apiFetch('/api/v1/computers/admin/notify/', {
          method: 'POST',
          body: JSON.stringify({ computer_id: Number(pc.id), text: notifyText.trim(), title: 'Сообщение от администратора' }),
        });
        toast(`Уведомление отправлено на ПК-${pc.alias}`, { type: 'success' });
      } else if (mode === 'power') {
        await apiFetch('/api/v1/computers/admin/commands/', {
          method: 'POST',
          body: JSON.stringify({
            computer_id: Number(pc.id),
            command_type: powerCmd,
            payload: {},
          }),
        });
        toast(`Команда «${powerCmd}» отправлена на ПК-${pc.alias}`, { type: 'success' });
      } else if (mode === 'postpay') {
        if (!rate || Number(rate) <= 0) { toast('Введите ставку сум/час', { type: 'warning' }); setBusy(false); return; }
        if (guestPostpaid) {
          // Walk-in guest: no client account. PC auto-unlocks as guest.
          await apiFetch('/api/v1/billing/admin/postpaid/guest/start/', {
            method: 'POST',
            body: JSON.stringify({ computer_id: Number(pc.id), rate_per_hour: Number(rate), club: clubId }),
          });
          toast(`Гостевая постоплата запущена (${rate} сум/ч) — ПК разблокируется`, { type: 'success' });
        } else {
          if (!userId) { toast('Выберите клиента или включите «Гость»', { type: 'warning' }); setBusy(false); return; }
          await apiFetch('/api/v1/billing/admin/postpaid/start/', {
            method: 'POST',
            body: JSON.stringify({ user_id: String(userId), rate_per_hour: Number(rate), club: clubId }),
          });
          toast(`Постоплата запущена (${rate} сум/ч)`, { type: 'success' });
        }
      } else if (mode === 'penalty') {
        if (!userId) { toast('Выберите клиента', { type: 'warning' }); setBusy(false); return; }
        if (!amount || Number(amount) <= 0) { toast('Введите сумму штрафа', { type: 'warning' }); setBusy(false); return; }
        await apiFetch('/api/v1/billing/admin/topup/', {
          method: 'POST',
          body: JSON.stringify({
            user_id: String(userId), amount_paid: Number(amount), minutes: 0,
            payment_method: method === 'card' ? 'card' : 'cash',
            note: `[PENALTY] ${penaltyReason || 'Штраф'}`, club: clubId,
          }),
        });
        toast(`Штраф ${amount} сум выписан`, { type: 'success' });
      } else if (mode === 'transfer') {
        if (!targetPc) { toast('Выберите целевой ПК', { type: 'warning' }); setBusy(false); return; }
        // Real session transfer: moves the active (guest postpaid) session to the
        // target PC keeping accrued time, locks the source, target auto-enters.
        const res = await apiFetch('/api/v1/computers/admin/session/transfer/', {
          method: 'POST',
          body: JSON.stringify({ source_computer_id: Number(pc.id), target_computer_id: Number(targetPc) }),
        });
        toast(res?.message || 'Клиент перенесён', { type: 'success' });
      } else if (mode === 'control') {
        await apiFetch('/api/v1/computers/admin/commands/', {
          method: 'POST',
          body: JSON.stringify({ computer_id: Number(pc.id), command_type: ctrlCmd, payload: {} }),
        });
        toast(`Команда управления отправлена на ПК-${pc.alias}`, { type: 'success' });
      } else if (mode === 'shell') {
        await apiFetch('/api/v1/computers/admin/commands/', {
          method: 'POST',
          body: JSON.stringify({ computer_id: Number(pc.id), command_type: shellCmd, payload: {} }),
        });
        toast(`Команда шелла отправлена на ПК-${pc.alias}`, { type: 'success' });
      }
      onDone && onDone();
      onClose();
    } catch (e) {
      toast(e.body?.message || e.body?.detail || e.body?.error || e.message || 'Ошибка', { type: 'error' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900,
      }}
    >
      <div style={{
        background: 'var(--bg-panel, #1a1f2e)', borderRadius: '14px',
        padding: '22px 24px', minWidth: '420px', maxWidth: '520px',
        border: '1px solid rgba(255,255,255,0.08)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: 32, height: 32, borderRadius: '8px',
              background: `${meta.accent}22`, display: 'flex',
              alignItems: 'center', justifyContent: 'center',
            }}>
              <Icon size={16} color={meta.accent} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '15px' }}>{meta.title}</h3>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>ПК-{pc?.alias}</div>
            </div>
          </div>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {mode === 'topup' && (
            <>
              <Field label="Клиент">
                <select value={userId} onChange={(e) => setUserId(e.target.value)} style={inputStyle}>
                  <option value="">— выберите —</option>
                  {users.map(u => (
                    <option key={u.id} value={u.id}>
                      {u.username} {u.phone ? `(${u.phone})` : ''}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Сумма, сум">
                <input type="number" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} style={inputStyle} />
              </Field>
              <Field label="Минуты">
                <input type="number" min="1" max="1440" value={minutes} onChange={(e) => setMinutes(e.target.value)} style={inputStyle} />
              </Field>
              <Field label="Способ">
                <select value={method} onChange={(e) => setMethod(e.target.value)} style={inputStyle}>
                  <option value="cash">Наличные</option>
                  <option value="card">Карта</option>
                </select>
              </Field>
              <Field label="Комментарий">
                <input type="text" value={note} onChange={(e) => setNote(e.target.value)} style={inputStyle} />
              </Field>
            </>
          )}

          {mode === 'booking' && (
            <>
              <Field label="Имя клиента">
                <input type="text" value={guestName} onChange={(e) => setGuestName(e.target.value)} style={inputStyle} />
              </Field>
              <Field label="Телефон">
                <input type="text" value={guestPhone} onChange={(e) => setGuestPhone(e.target.value)} placeholder="+7..." style={inputStyle} />
              </Field>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <Field label="С">
                  <input type="datetime-local" value={fromAt} onChange={(e) => setFromAt(e.target.value)} style={inputStyle} />
                </Field>
                <Field label="До">
                  <input type="datetime-local" value={toAt} onChange={(e) => setToAt(e.target.value)} style={inputStyle} />
                </Field>
              </div>
              <Field label="Комментарий">
                <input type="text" value={note} onChange={(e) => setNote(e.target.value)} style={inputStyle} />
              </Field>
            </>
          )}

          {mode === 'notify' && (
            <Field label="Текст уведомления">
              <textarea
                value={notifyText}
                onChange={(e) => setNotifyText(e.target.value)}
                rows={4}
                placeholder="Например: «Подойдите на ресепшен»"
                style={{ ...inputStyle, resize: 'vertical' }}
              />
            </Field>
          )}

          {mode === 'power' && (
            <Field label="Команда">
              <select value={powerCmd} onChange={(e) => setPowerCmd(e.target.value)} style={inputStyle}>
                <option value="reboot">Перезагрузить</option>
                <option value="shutdown">Выключить</option>
                <option value="wol">Включить (Wake-on-LAN)</option>
                <option value="lock">Заблокировать</option>
                <option value="unlock">Разблокировать</option>
              </select>
            </Field>
          )}

          {mode === 'postpay' && (
            <>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px',
                cursor: 'pointer', padding: '4px 0' }}>
                <input type="checkbox" checked={guestPostpaid}
                  onChange={(e) => setGuestPostpaid(e.target.checked)} style={{ cursor: 'pointer' }} />
                Гость (без аккаунта) — ПК сразу разблокируется
              </label>
              {!guestPostpaid && (
                <Field label="Клиент">
                  <select value={userId} onChange={(e) => setUserId(e.target.value)} style={inputStyle}>
                    <option value="">— выберите —</option>
                    {users.map(u => <option key={u.id} value={u.id}>{u.username} {u.phone ? `(${u.phone})` : ''}</option>)}
                  </select>
                </Field>
              )}
              <Field label="Ставка, сум/час">
                <input type="number" min="0" step="10" value={rate} onChange={(e) => setRate(e.target.value)} style={inputStyle} />
              </Field>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {guestPostpaid
                  ? 'Гость садится и сразу играет в кредит. Минуты считаются; оплата на стойке при закрытии.'
                  : 'Клиент играет в кредит — оплата при завершении сеанса.'}
              </div>
            </>
          )}

          {mode === 'penalty' && (
            <>
              <Field label="Клиент">
                <select value={userId} onChange={(e) => setUserId(e.target.value)} style={inputStyle}>
                  <option value="">— выберите —</option>
                  {users.map(u => <option key={u.id} value={u.id}>{u.username} {u.phone ? `(${u.phone})` : ''}</option>)}
                </select>
              </Field>
              <Field label="Сумма штрафа, сум">
                <input type="number" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} style={inputStyle} />
              </Field>
              <Field label="Причина">
                <input type="text" value={penaltyReason} onChange={(e) => setPenaltyReason(e.target.value)}
                  placeholder="Поздняя отмена брони, порча оборудования…" style={inputStyle} />
              </Field>
              <Field label="Способ">
                <select value={method} onChange={(e) => setMethod(e.target.value)} style={inputStyle}>
                  <option value="cash">Наличные</option>
                  <option value="card">Карта</option>
                </select>
              </Field>
            </>
          )}

          {mode === 'transfer' && (
            <Field label="Пересадить на">
              <select value={targetPc} onChange={(e) => setTargetPc(e.target.value)} style={inputStyle}>
                <option value="">— выберите ПК —</option>
                {computers.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.name} {(c.status === 'online') ? '(занят)' : '(свободен)'}
                  </option>
                ))}
              </select>
            </Field>
          )}

          {mode === 'control' && (
            <Field label="Действие">
              {/* Only actions with a real backend CommandType + shell handler.
                  VNC / диспетчер задач / скриншот требуют отдельной интеграции —
                  не предлагаем гарантированно падающие действия. Сообщение —
                  отдельное действие «Уведомление». */}
              <select value={ctrlCmd} onChange={(e) => setCtrlCmd(e.target.value)} style={inputStyle}>
                <option value="kill_games">Закрыть игры</option>
              </select>
            </Field>
          )}

          {mode === 'shell' && (
            <Field label="Команда шелла">
              {/* Canonical CommandType values handled by the shell's KioskCommandHandler. */}
              <select value={shellCmd} onChange={(e) => setShellCmd(e.target.value)} style={inputStyle}>
                <option value="lock">Заблокировать шелл</option>
                <option value="high_access">Высокий доступ (рабочий стол)</option>
                <option value="high_access_off">Снять высокий доступ</option>
                <option value="update_app">Обновить шелл</option>
              </select>
            </Field>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '20px' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={busy}>Отмена</button>
          <button
            className="btn btn-primary"
            onClick={submit}
            disabled={busy}
            style={{ background: meta.accent, borderColor: meta.accent }}
          >
            {busy ? '...' : meta.title}
          </button>
        </div>
      </div>
    </div>
  );
};

const Field = ({ label, children }) => (
  <div>
    <label style={{ display: 'block', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
      {label}
    </label>
    {children}
  </div>
);

const inputStyle = {
  width: '100%', background: 'var(--bg-dark, #0f1219)',
  border: '1px solid var(--border-color, rgba(255,255,255,0.08))',
  borderRadius: '8px', padding: '9px 12px',
  color: 'var(--text-light, white)', fontSize: '13px',
  fontFamily: 'inherit',
  boxSizing: 'border-box',
};

export default PcActionModal;
