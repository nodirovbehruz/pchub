import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Monitor, RefreshCw, Search, X, Cpu, HardDrive, Wifi, Activity,
  CheckSquare, Square, Power, Send, Circle, Map, List, Plus,
  ChevronRight, Edit2, Trash2, Wrench, Calendar, Clock,
  AlertTriangle, WifiOff, Settings, Bell, Zap, TerminalSquare,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';
import PcActionModal from '../components/PcActionModal';

/* ─── helpers ─────────────────────────────────────────────────────────── */
const fmtTime = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }); }
  catch { return '—'; }
};
const fmtHoursLeft = (min) => {
  if (min == null) return '—';
  const h = Math.floor(min / 60), m = min % 60;
  return h > 0 ? `${h}ч ${m}м` : `${m}м`;
};
const endTimeFromSession = (session) => {
  if (!session || session.time_left_minutes == null) return null;
  const d = new Date(Date.now() + session.time_left_minutes * 60000);
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
};

/* ─── status ──────────────────────────────────────────────────────────── */
const STATUS_CFG = {
  BUSY:        { label: 'Занят',         color: '#6366f1', bg: 'rgba(99,102,241,0.12)' },
  BOOKED:      { label: 'Есть бронь',    color: '#3b82f6', bg: 'rgba(59,130,246,0.12)' },
  ONLINE:      { label: 'Включён',       color: '#10b981', bg: 'rgba(16,185,129,0.12)' },
  OFFLINE:     { label: 'Выключен',      color: '#6b7280', bg: 'rgba(107,114,128,0.12)' },
  MAINTENANCE: { label: 'Обслуживание',  color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  DISABLED:    { label: 'Нет связи',     color: '#ef4444', bg: 'rgba(239,68,68,0.12)' },
};
const getStatus = (pc) => {
  if (pc.active_session) return 'BUSY';
  if (pc.next_booking)   return 'BOOKED';
  return pc.status === 'ONLINE' ? 'ONLINE'
       : pc.status === 'MAINTENANCE' ? 'MAINTENANCE'
       : pc.status === 'DISABLED'    ? 'DISABLED'
       : 'OFFLINE';
};

const StatusBadge = ({ pc }) => {
  const cfg = STATUS_CFG[getStatus(pc)] || STATUS_CFG.OFFLINE;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px',
      padding: '2px 8px', borderRadius: '999px', fontSize: '11px', fontWeight: 600,
      background: cfg.bg, color: cfg.color }}>
      <Circle size={6} fill={cfg.color} stroke="none" />
      {cfg.label}
    </span>
  );
};

/* ─── Context menu ────────────────────────────────────────────────────── */
const ContextMenu = ({ pc, x, y, onClose, onAction, onOpenNotif, onOpenEdit, onOpenTariff }) => {
  const [sub, setSub] = useState(null);
  const ref = useRef();
  const hasSession = !!pc.active_session;
  // A PC can be occupied without an active_session record (status stuck on
  // ONLINE after a guest/postpaid start, shell logged in, etc.). "Завершить
  // сеанс" must stay clickable in those cases — the backend frees the PC safely.
  const statusUp = String(pc.status || '').toUpperCase();
  const occupied = hasSession || ['ONLINE', 'BUSY', 'OCCUPIED', 'LOCKED', 'IN_USE'].includes(statusUp);

  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose(); };
    document.addEventListener('mousedown', h);
    document.addEventListener('contextmenu', h);
    return () => { document.removeEventListener('mousedown', h); document.removeEventListener('contextmenu', h); };
  }, [onClose]);

  const Item = ({ label, icon: Icon, disabled, danger, submenu, onClick }) => (
    <div
      // Hovering an item with a submenu OPENS it; hovering an item that itself
      // has another submenu switches to it. Items WITHOUT a submenu (incl. the
      // sub-items themselves) must NOT clear `sub` — otherwise moving the cursor
      // onto the submenu instantly closes it and you can't click anything.
      onMouseEnter={() => { if (submenu) setSub(submenu); }}
      onClick={disabled ? undefined : onClick}
      style={{
        padding: '7px 14px', fontSize: '13px', cursor: disabled ? 'default' : 'pointer',
        display: 'flex', alignItems: 'center', gap: '8px', borderRadius: '6px',
        color: danger ? '#ef4444' : disabled ? 'rgba(255,255,255,0.25)' : 'var(--text-main)',
        background: sub === submenu && submenu ? 'var(--hover-overlay)' : 'transparent',
      }}
      onMouseOver={e => { if (!disabled) e.currentTarget.style.background = 'var(--hover-overlay)'; }}
      onMouseOut={e => { if (sub !== submenu) e.currentTarget.style.background = 'transparent'; }}
    >
      {Icon && <Icon size={13} style={{ flexShrink: 0 }} />}
      <span style={{ flex: 1 }}>{label}</span>
      {submenu && <ChevronRight size={11} style={{ color: 'var(--text-muted)' }} />}
    </div>
  );

  const Divider = () => <div style={{ height: '1px', background: 'var(--border-color)', margin: '4px 0' }} />;

  const MAIN_W = 220, SUB_W = 200;
  const mainLeft = Math.min(x, window.innerWidth - MAIN_W - 12);
  const mainTop = Math.min(y, window.innerHeight - 400);
  // Flip the submenu to the LEFT of the main menu when opening it to the right
  // would run off the screen edge (e.g. the detail panel is open on the right).
  const subOpensLeft = mainLeft + MAIN_W + 4 + SUB_W > window.innerWidth - 8;

  const menuStyle = {
    position: 'fixed', left: mainLeft, top: mainTop,
    width: MAIN_W, background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
    borderRadius: '10px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)', zIndex: 2000, padding: '6px',
  };
  const subStyle = (yOff) => ({
    position: 'fixed',
    left: subOpensLeft ? Math.max(8, mainLeft - SUB_W - 4) : mainLeft + MAIN_W + 4,
    top: Math.min(mainTop + yOff, window.innerHeight - 200),
    width: SUB_W, background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
    borderRadius: '10px', boxShadow: '0 8px 32px rgba(0,0,0,0.4)', zIndex: 2001, padding: '6px',
  });

  return (
    <div ref={ref}>
      <div style={menuStyle}>
        <Item label="Выбрать тариф"   icon={Clock}          onClick={() => { onOpenTariff(pc); onClose(); }} />
        <Item label="Постоплата"      icon={Clock}          disabled={hasSession} onClick={() => { onAction(pc.id, 'postpay'); onClose(); }} />
        <Item label="Пополнить депозит" icon={Plus}         disabled={!hasSession} onClick={() => { onAction(pc.id, 'deposit'); onClose(); }} />
        <Divider />
        <Item label="Бронирование"    icon={Calendar}       submenu="booking" />
        <Item label="Штраф"           icon={AlertTriangle}  submenu="fine"    disabled={!hasSession} />
        <Item label="Смена места"     icon={ChevronRight}   disabled={!hasSession} onClick={() => { onAction(pc.id, 'move'); onClose(); }} />
        <Divider />
        <Item label="Завершить сеанс" icon={X}              danger disabled={!occupied} onClick={() => { onAction(pc.id, 'stop_session'); onClose(); }} />
        <Divider />
        <Item label="Уведомление"     icon={Bell}           onClick={() => { onOpenNotif(pc); onClose(); }} />
        <Item label="Электропитание"  icon={Zap}            submenu="power" />
        <Item label="Управление ПК"   icon={Settings}       submenu="manage" />
        <Item label="Шелл"            icon={TerminalSquare} submenu="shell" />
      </div>

      {/* Submenus */}
      {sub === 'booking' && (
        <div style={subStyle(96)}>
          <Item label="Забронировать"         icon={Calendar} onClick={() => { onAction(pc.id, 'book'); onClose(); }} />
          <Item label="Список бронирований"   icon={List}     onClick={() => { onAction(pc.id, 'bookings_list'); onClose(); }} />
          <Item label="Клиент пришёл"         icon={Circle}   onClick={() => { onAction(pc.id, 'client_arrived'); onClose(); }} />
        </div>
      )}
      {sub === 'fine' && (
        <div style={subStyle(124)}>
          {['5 мин.', '10 мин.', '15 мин.', '30 мин.'].map((t, i) => (
            <Item key={t} label={t} icon={AlertTriangle}
              onClick={() => { onAction(pc.id, `fine_${[5,10,15,30][i]}`); onClose(); }} />
          ))}
        </div>
      )}
      {sub === 'power' && (
        <div style={subStyle(206)}>
          <Item label="Включить"          icon={Power}    onClick={() => { onAction(pc.id, 'wake'); onClose(); }} />
          <Item label="Выключить"         icon={Power}    onClick={() => { onAction(pc.id, 'shutdown'); onClose(); }} />
          <Item label="Выйти из системы"  icon={Power}    onClick={() => { onAction(pc.id, 'logout_os'); onClose(); }} />
          <Item label="Перезагрузить"     icon={RefreshCw} onClick={() => { onAction(pc.id, 'reboot'); onClose(); }} />
        </div>
      )}
      {sub === 'manage' && (
        <div style={subStyle(234)}>
          <Item label="Вкл. режим обслуживания" icon={Wrench}   onClick={() => { onAction(pc.id, 'maintenance'); onClose(); }} />
          <Item label="Подключиться к ПК"       icon={Monitor}  disabled onClick={() => {}} />
          <Item label="Просмотр экрана"          icon={Monitor}  disabled onClick={() => {}} />
          <Item label="Заметка о ПК"             icon={Edit2}    onClick={() => { onAction(pc.id, 'note'); onClose(); }} />
          <Divider />
          <Item label="Редактировать"            icon={Edit2}    onClick={() => { onOpenEdit(pc); onClose(); }} />
          <Item label="Удалить"                  icon={Trash2}   danger onClick={() => { onAction(pc.id, 'delete'); onClose(); }} />
        </div>
      )}
      {sub === 'shell' && (
        <div style={subStyle(262)}>
          <Item label="Поделиться логами" icon={Send}            onClick={() => { onAction(pc.id, 'share_logs'); onClose(); }} />
          <Item label={pc.high_access_active ? 'Высокий доступ: выкл.' : 'Высокий доступ'} icon={Settings} onClick={() => { onAction(pc.id, 'high_access'); onClose(); }} />
          <Item label="Отключить шелл"    icon={WifiOff}  danger onClick={() => { onAction(pc.id, 'disconnect_shell'); onClose(); }} />
        </div>
      )}
    </div>
  );
};

/* ─── PC Tile for map view ────────────────────────────────────────────── */
const PcTile = ({ pc, isSelected, onClick, onContextMenu }) => {
  const st = getStatus(pc);
  const session = pc.active_session;
  const booking = pc.next_booking;
  const endTime = endTimeFromSession(session);

  const tileStyle = useMemo(() => {
    const base = {
      width: 82, height: 82, borderRadius: 10, border: '1px solid',
      cursor: 'pointer', position: 'relative', display: 'flex',
      flexDirection: 'column', padding: '7px 8px', userSelect: 'none',
      transition: 'opacity 0.15s, box-shadow 0.15s',
      boxShadow: isSelected ? '0 0 0 2px #6366f1' : 'none',
    };
    if (st === 'BUSY')        return { ...base, background: 'rgba(99,102,241,0.75)',  borderColor: '#6366f1', color: '#fff' };
    if (st === 'BOOKED')      return { ...base, background: 'rgba(59,130,246,0.18)',  borderColor: '#3b82f6', color: '#93c5fd' };
    if (st === 'ONLINE')      return { ...base, background: 'var(--bg-panel)',         borderColor: '#10b981', color: 'var(--text-main)' };
    if (st === 'MAINTENANCE') return { ...base, background: 'rgba(245,158,11,0.15)',  borderColor: '#f59e0b', color: '#fbbf24' };
    if (st === 'DISABLED')    return { ...base, background: 'rgba(239,68,68,0.12)',   borderColor: '#ef4444', color: '#fca5a5' };
    return { ...base, background: 'var(--bg-dark)', borderColor: 'var(--border-color)', color: 'var(--text-muted)' };
  }, [st, isSelected]);

  return (
    <div style={tileStyle} onClick={onClick} onContextMenu={onContextMenu}>
      {/* PC number */}
      <div style={{ fontWeight: 700, fontSize: '15px', lineHeight: 1 }}>
        {pc.pc_number || pc.id}
      </div>

      {/* Status icon top-right */}
      <div style={{ position: 'absolute', top: 6, right: 7 }}>
        {st === 'OFFLINE'     && <Power size={13} />}
        {st === 'MAINTENANCE' && <Wrench size={13} />}
        {st === 'BOOKED'      && <Calendar size={13} />}
        {st === 'DISABLED'    && <WifiOff size={13} />}
      </div>

      {/* Bottom info */}
      <div style={{ marginTop: 'auto', fontSize: '11px', lineHeight: 1.3 }}>
        {st === 'BUSY' && session?.is_postpaid && (
          <span style={{ fontSize: '10px' }}>⏱ {fmtHoursLeft(session.minutes_played || 0)}</span>
        )}
        {st === 'BUSY' && !session?.is_postpaid && endTime && <span>до {endTime}</span>}
        {st === 'BOOKED' && booking   && <span style={{ fontSize: '10px' }}>с {fmtTime(booking.from_at)}</span>}
        {st === 'ONLINE' && <span style={{ fontSize: '10px', color: '#10b981' }}>Свободен</span>}
      </div>

      {/* Name below number */}
      <div style={{ fontSize: '10px', color: st === 'BUSY' ? 'rgba(255,255,255,0.7)' : 'var(--text-muted)',
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {pc.name}
      </div>
    </div>
  );
};

/* ─── Live postpaid meter (counts UP from session start) ──────────────── */
const usePostpaidTick = (startedAt, isPostpaid) => {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!isPostpaid) return undefined;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [isPostpaid]);
  if (!startedAt) return { mmss: '00:00:00', minutes: 0, ms: 0 };
  const ms = Math.max(0, now - new Date(startedAt).getTime());
  const totalSec = Math.floor(ms / 1000);
  const h = String(Math.floor(totalSec / 3600)).padStart(2, '0');
  const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0');
  const s = String(totalSec % 60).padStart(2, '0');
  return { mmss: `${h}:${m}:${s}`, minutes: Math.floor(totalSec / 60), ms };
};

const PostpaidMeter = ({ session }) => {
  const { mmss, ms } = usePostpaidTick(session.started_at, true);
  const rate = Number(session.postpaid_rate || 0);
  const amount = (rate * ms / 3_600_000).toFixed(2);
  return (
    <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
      <div>
        <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Играет (постоплата)</div>
        <div style={{ fontSize: '15px', fontWeight: 700, color: '#f59e0b', fontVariantNumeric: 'tabular-nums' }}>{mmss}</div>
      </div>
      <div>
        <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>К оплате</div>
        <div style={{ fontSize: '15px', fontWeight: 700, color: '#f59e0b' }}>{amount} сум</div>
        {rate > 0 && <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{rate} сум/час</div>}
      </div>
    </div>
  );
};

/* ─── Close postpaid dialog (amount due + payment method) ─────────────── */
const PAY_METHODS = [
  { id: 'cash',     label: 'Наличные' },
  { id: 'card',     label: 'Карта' },
  { id: 'transfer', label: 'Перевод' },
];
const ClosePostpaidModal = ({ pc, onClose, onDone }) => {
  const { toast } = useToast();
  const session = pc.active_session || {};
  const { mmss, ms } = usePostpaidTick(session.started_at, true);
  const rate = Number(session.postpaid_rate || 0);
  const amount = (rate * ms / 3_600_000).toFixed(2);
  const [method, setMethod] = useState('cash');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      const res = await apiFetch('/api/v1/computers/admin/session/stop/', {
        method: 'POST', body: JSON.stringify({ computer_id: pc.id, payment_method: method }),
      });
      toast(res?.message || 'Сеанс завершён', { type: 'success' });
      onDone();
    } catch (e) {
      toast(e.body ? Object.values(e.body).flat().join(', ') : (e.message || 'Ошибка'), { type: 'error' });
      setBusy(false);
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 3000,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ width: 380, background: 'var(--bg-panel)',
        border: '1px solid var(--border-color)', borderRadius: 14, padding: 22 }}>
        <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>Завершение постоплаты</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
          {pc.name} · ПК #{pc.pc_number || pc.id}
        </div>

        <div style={{ display: 'flex', gap: 12, marginBottom: 18 }}>
          <div style={{ flex: 1, background: 'var(--bg-dark)', borderRadius: 10, padding: '12px 14px' }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Сыграно</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b', fontVariantNumeric: 'tabular-nums' }}>{mmss}</div>
          </div>
          <div style={{ flex: 1, background: 'var(--bg-dark)', borderRadius: 10, padding: '12px 14px' }}>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>К оплате</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#10b981' }}>{amount} сум</div>
            {rate > 0 && <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{rate} сум/час</div>}
          </div>
        </div>

        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Способ оплаты</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 22 }}>
          {PAY_METHODS.map(m => (
            <button key={m.id} onClick={() => setMethod(m.id)} style={{
              flex: 1, padding: '10px 0', borderRadius: 9, fontSize: 13, fontWeight: 600, cursor: 'pointer',
              border: '1px solid ' + (method === m.id ? '#6366f1' : 'var(--border-color)'),
              background: method === m.id ? 'rgba(99,102,241,0.15)' : 'transparent',
              color: method === m.id ? '#a5b4fc' : 'var(--text-main)',
            }}>{m.label}</button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-secondary" style={{ flex: 1, justifyContent: 'center' }} onClick={onClose} disabled={busy}>
            Отмена
          </button>
          <button className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }} onClick={submit} disabled={busy}>
            {busy ? 'Закрытие…' : `Принять ${amount} сум`}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Right detail panel ──────────────────────────────────────────────── */
const PcDetailPanel = ({ pc, onClose, onAction, onOpenNotif, onOpenTariff }) => {
  const session = pc.active_session;
  const booking = pc.next_booking;
  return (
    <div style={{ width: 300, flexShrink: 0, background: 'var(--bg-panel)',
      borderLeft: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-color)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: '15px' }}>{pc.name}</div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: 2 }}>
            {pc.group_name || 'Без зоны'} · ПК #{pc.pc_number || pc.id}
          </div>
        </div>
        <button className="icon-btn" onClick={onClose}><X size={15} /></button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Status */}
        <div>
          <StatusBadge pc={pc} />
          {pc.last_seen && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: 4 }}>
              Активность: {new Date(pc.last_seen).toLocaleString('ru-RU', { day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit' })}
            </div>
          )}
        </div>

        {/* Active session */}
        {session && (
          <div style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
            borderRadius: 10, padding: 12 }}>
            <div style={{ fontSize: '11px', color: '#818cf8', fontWeight: 600, textTransform: 'uppercase',
              letterSpacing: '0.5px', marginBottom: 8 }}>Активный сеанс</div>
            <div style={{ fontWeight: 600, fontSize: '13px' }}>{session.client || 'Гость'}</div>
            {session.tariff && <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Тариф: {session.tariff}</div>}
            {session.is_postpaid ? (
              <>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: 6 }}>
                  Начало: {fmtTime(session.started_at)}
                </div>
                <PostpaidMeter session={session} />
              </>
            ) : (
              <div style={{ display: 'flex', gap: 16, marginTop: 8 }}>
                <div><div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Начало</div>
                  <div style={{ fontSize: '12px', fontWeight: 600 }}>{fmtTime(session.started_at)}</div></div>
                <div><div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Окончание</div>
                  <div style={{ fontSize: '12px', fontWeight: 600 }}>{endTimeFromSession(session) || '—'}</div></div>
                <div><div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Осталось</div>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: session.time_left_minutes < 15 ? '#f59e0b' : '#10b981' }}>
                    {fmtHoursLeft(session.time_left_minutes)}</div></div>
              </div>
            )}
          </div>
        )}

        {/* Booking */}
        {booking && !session && (
          <div style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)',
            borderRadius: 10, padding: 12 }}>
            <div style={{ fontSize: '11px', color: '#60a5fa', fontWeight: 600, textTransform: 'uppercase',
              letterSpacing: '0.5px', marginBottom: 6 }}>Бронь</div>
            <div style={{ fontWeight: 600, fontSize: '13px' }}>{booking.client || '—'}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{fmtTime(booking.from_at)}
              {booking.starts_in_minutes != null && ` (через ${fmtHoursLeft(booking.starts_in_minutes)})`}
            </div>
          </div>
        )}

        {/* Hardware */}
        <div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600,
            textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 8 }}>Конфигурация</div>
          {[
            { icon: Cpu,       label: 'Процессор', value: pc.cpu_model },
            { icon: Activity,  label: 'ОП',        value: pc.ram_total_gb ? `${pc.ram_total_gb} ГБ` : null },
            { icon: Monitor,   label: 'Видеокарта', value: pc.gpu_model },
            { icon: HardDrive, label: 'Диски',      value: pc.storage_total_gb ? `${pc.storage_total_gb} ГБ` : null },
            { icon: Wifi,      label: 'IP',         value: pc.ip_address },
          ].filter(r => r.value).map(({ icon: Icon, label, value }) => (
            <div key={label} style={{ display: 'flex', justifyContent: 'space-between',
              fontSize: '12px', marginBottom: 5, alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: 6, color: 'var(--text-muted)', alignItems: 'center' }}>
                <Icon size={11} /> {label}
              </div>
              <div style={{ fontWeight: 500, maxWidth: 170, textAlign: 'right',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</div>
            </div>
          ))}
        </div>

        {/* Shell */}
        {(pc.current_app || pc.shell_version) && (
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600,
              textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 6 }}>Шелл</div>
            {pc.current_app && <div style={{ fontSize: '12px' }}>Приложение: <b>{pc.current_app}</b></div>}
            {pc.shell_version && <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Версия: {pc.shell_version}</div>}
          </div>
        )}
      </div>

      {/* Footer actions */}
      <div style={{ padding: '10px 14px', borderTop: '1px solid var(--border-color)', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <button className="btn btn-primary" style={{ flex: 1, fontSize: '12px', justifyContent: 'center' }}
          onClick={() => onOpenTariff(pc)}>
          <Clock size={12} /> Тариф
        </button>
        {pc.active_session && (
          <button className="btn btn-secondary" style={{ flex: 1, fontSize: '12px', justifyContent: 'center',
            borderColor: '#ef4444', color: '#ef4444' }}
            onClick={() => onAction(pc.id, 'stop_session')}>
            <X size={12} /> Завершить
          </button>
        )}
        <button className="btn btn-secondary" style={{ flex: 1, fontSize: '12px', justifyContent: 'center' }}
          onClick={() => onOpenNotif(pc)}>
          <Bell size={12} /> Уведомить
        </button>
        <button className="btn btn-secondary" style={{ flex: '0 0 100%', fontSize: '12px', justifyContent: 'center' }}
          onClick={() => onAction(pc.id, 'reboot')}>
          <RefreshCw size={12} /> Перезагрузить
        </button>
      </div>
    </div>
  );
};

/* ─── Table view ──────────────────────────────────────────────────────── */
const TableView = ({ groups, computers, selectedIds, onToggle, onToggleGroup, onToggleAll,
  allFilteredIds, onContextMenu, onSelectPc, activePcId }) => {

  const grouped = useMemo(() => {
    const map = {};
    groups.forEach(g => { map[g.id] = { ...g, pcs: [] }; });
    map['__none'] = { id: '__none', name: 'Без группы', color: '#6b7280', pcs: [] };
    computers.forEach(pc => {
      const key = pc.group || '__none';
      if (map[key]) map[key].pcs.push(pc);
      else map['__none'].pcs.push(pc);
    });
    return Object.values(map).filter(g => g.pcs.length > 0);
  }, [groups, computers]);

  const cols = ['№', 'Название', 'Статус', 'Бронь', 'Клиент', 'Сеанс', 'Старт', 'Окончание', 'Остаток', 'Приложение', 'Версия'];

  return (
    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 12, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-dark)' }}>
            <th style={{ padding: '10px 16px', width: 36 }}>
              <button onClick={onToggleAll} style={{ background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--text-muted)', display: 'flex', padding: 0 }}>
                {selectedIds.size === allFilteredIds.length && allFilteredIds.length > 0
                  ? <CheckSquare size={14} color="var(--accent)" />
                  : <Square size={14} />}
              </button>
            </th>
            {cols.map(c => (
              <th key={c} style={{ padding: '10px 10px', textAlign: 'left', fontSize: '10px',
                color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase',
                letterSpacing: '0.5px', whiteSpace: 'nowrap' }}>
                {c}
              </th>
            ))}
            <th style={{ width: 36 }} />
          </tr>
        </thead>
        <tbody>
          {grouped.map(group => (
            <>
              {/* Group header */}
              <tr key={`grp-${group.id}`} style={{ background: 'rgba(255,255,255,0.02)',
                borderBottom: '1px solid var(--border-color)' }}>
                <td colSpan={13} style={{ padding: '6px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Circle size={8} fill={group.color || '#6b7280'} stroke="none" />
                    <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase',
                      letterSpacing: '0.08em', color: 'var(--text-muted)' }}>
                      {group.name}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', opacity: 0.5 }}>
                      {group.pcs.length} хостов
                    </span>
                    <div style={{ flex: 1 }} />
                    <button onClick={() => onToggleGroup(group.pcs.map(p => p.id))}
                      style={{ fontSize: '11px', color: 'var(--text-muted)', background: 'none',
                        border: 'none', cursor: 'pointer', padding: '2px 6px' }}>
                      Выбрать все
                    </button>
                  </div>
                </td>
              </tr>

              {/* PC rows */}
              {group.pcs.map(pc => {
                const session = pc.active_session;
                const isSel = selectedIds.has(pc.id);
                const isActive = activePcId === pc.id;
                const endT = endTimeFromSession(session);
                return (
                  <tr key={pc.id}
                    onClick={() => onSelectPc(pc)}
                    onContextMenu={e => { e.preventDefault(); onContextMenu(e, pc); }}
                    style={{ borderBottom: '1px solid var(--border-row)',
                      background: isActive ? 'rgba(99,102,241,0.06)' : isSel ? 'rgba(99,102,241,0.04)' : 'transparent',
                      cursor: 'pointer' }}
                    onMouseEnter={e => { if (!isActive && !isSel) e.currentTarget.style.background = 'var(--hover-overlay)'; }}
                    onMouseLeave={e => { if (!isActive && !isSel) e.currentTarget.style.background = 'transparent'; }}>
                    <td style={{ padding: '9px 16px' }} onClick={e => { e.stopPropagation(); onToggle(pc.id); }}>
                      {isSel ? <CheckSquare size={13} color="var(--accent)" /> : <Square size={13} color="var(--text-muted)" />}
                    </td>
                    <td style={{ padding: '9px 10px', color: 'var(--text-muted)', fontWeight: 500 }}>
                      {pc.pc_number || pc.id}
                    </td>
                    <td style={{ padding: '9px 10px', fontWeight: 600, maxWidth: 120,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {pc.name}
                    </td>
                    <td style={{ padding: '9px 10px' }}><StatusBadge pc={pc} /></td>
                    <td style={{ padding: '9px 10px', color: pc.next_booking ? '#3b82f6' : 'var(--text-muted)' }}>
                      {pc.next_booking ? <span style={{ fontSize: '11px', padding: '2px 6px',
                        background: 'rgba(59,130,246,0.1)', borderRadius: 6 }}>Есть бронь</span> : '—'}
                    </td>
                    <td style={{ padding: '9px 10px', color: session ? 'var(--text-main)' : 'var(--text-muted)' }}>
                      {session?.client || '—'}
                    </td>
                    <td style={{ padding: '9px 10px', color: 'var(--text-muted)' }}>
                      {session?.tariff || '—'}
                    </td>
                    <td style={{ padding: '9px 10px', color: 'var(--text-muted)' }}>
                      {session ? fmtTime(session.started_at) : '—'}
                    </td>
                    <td style={{ padding: '9px 10px', color: 'var(--text-muted)' }}>
                      {endT || '—'}
                    </td>
                    <td style={{ padding: '9px 10px', fontWeight: 600,
                      color: session?.time_left_minutes < 15 ? '#f59e0b' : '#10b981' }}>
                      {session ? fmtHoursLeft(session.time_left_minutes) : '—'}
                    </td>
                    <td style={{ padding: '9px 10px', color: 'var(--text-muted)',
                      maxWidth: 110, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {pc.current_app || '—'}
                    </td>
                    <td style={{ padding: '9px 10px', color: 'var(--text-muted)' }}>
                      {pc.shell_version || '—'}
                    </td>
                    <td style={{ padding: '9px 8px' }}>
                      <button className="icon-btn" style={{ width: 24, height: 24 }}
                        onClick={e => { e.stopPropagation(); onContextMenu(e, pc); }}>
                        <ChevronRight size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
};

/* ─── Map view ────────────────────────────────────────────────────────── */
const MapView = ({ groups, computers, selectedIds, onSelectPc, activePcId, onContextMenu }) => {
  const grouped = useMemo(() => {
    const map = {};
    groups.forEach(g => { map[g.id] = { ...g, pcs: [] }; });
    map['__none'] = { id: '__none', name: 'Без группы', color: '#6b7280', pcs: [] };
    computers.forEach(pc => {
      const key = pc.group || '__none';
      if (map[key]) map[key].pcs.push(pc);
      else map['__none'].pcs.push(pc);
    });
    return Object.values(map).filter(g => g.pcs.length > 0);
  }, [groups, computers]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {grouped.map(group => (
        <div key={group.id}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <Circle size={8} fill={group.color || '#6b7280'} stroke="none" />
            <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase',
              letterSpacing: '0.08em', color: 'var(--text-muted)' }}>
              {group.name}
            </span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', opacity: 0.5 }}>
              {group.pcs.length}
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {group.pcs.map(pc => (
              <PcTile
                key={pc.id}
                pc={pc}
                isSelected={activePcId === pc.id || selectedIds.has(pc.id)}
                onClick={() => onSelectPc(pc)}
                onContextMenu={e => { e.preventDefault(); onContextMenu(e, pc); }}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

/* ─── Notification modal ──────────────────────────────────────────────── */
const NotifModal = ({ pc, onClose, onSend }) => {
  const [text, setText] = useState('');
  return (
    <div onClick={e => e.target === e.currentTarget && onClose()}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 14, width: 420,
        border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border-color)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: '15px' }}>Уведомление для</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{pc.name}:</div>
          </div>
          <button className="icon-btn" onClick={onClose}><X size={15} /></button>
        </div>
        <div style={{ padding: '18px 22px' }}>
          <textarea value={text} onChange={e => setText(e.target.value)}
            placeholder="Ваше сообщение"
            rows={4} style={{ width: '100%', resize: 'vertical', background: 'var(--bg-dark)',
              border: '1px solid var(--border-color)', borderRadius: 8, padding: '10px 12px',
              color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit', boxSizing: 'border-box' }} />
        </div>
        <div style={{ padding: '0 22px 18px', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => onSend(text)}>
            Отправить
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Edit/Create PC modal ────────────────────────────────────────────── */
const EditPcModal = ({ pc, groups, clubId, onClose, onSaved }) => {
  const { toast } = useToast();
  const [name, setName]   = useState(pc?.name || '');
  const [group, setGroup] = useState(pc?.group || '');
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!name.trim()) { toast('Введите название', { type: 'warning' }); return; }
    setSaving(true);
    try {
      if (pc) {
        await apiFetch(`/api/v1/computers/${pc.id}/`, { method: 'PATCH',
          body: JSON.stringify({ name: name.trim(), group: group || null }) });
        toast('ПК обновлён', { type: 'success' });
      } else {
        await apiFetch(`/api/v1/computers/`, { method: 'POST',
          body: JSON.stringify({ name: name.trim(), group: group || null, club: Number(clubId) }) });
        toast('ПК создан', { type: 'success' });
      }
      onSaved();
    } catch (e) { toast(e.message, { type: 'error' }); }
    finally { setSaving(false); }
  };

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 14, width: 360,
        border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border-color)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>
            {pc ? 'Редактирование' : 'Создание'}
          </h3>
          <button className="icon-btn" onClick={onClose}><X size={15} /></button>
        </div>
        <div style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>
              Название <span style={{ float: 'right' }}>{name.length}/32</span>
            </label>
            <input value={name} onChange={e => setName(e.target.value.slice(0, 32))}
              placeholder="PC-01"
              style={{ height: 38, padding: '0 12px', width: '100%', boxSizing: 'border-box',
                background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                borderRadius: 8, color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit' }} />
          </div>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>
              Группа
            </label>
            <select value={group} onChange={e => setGroup(e.target.value)}
              style={{ height: 38, padding: '0 12px', width: '100%', boxSizing: 'border-box',
                background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                borderRadius: 8, color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit' }}>
              <option value="">Без группы</option>
              {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          </div>
          <button className="btn btn-primary" style={{ marginTop: 4 }} onClick={save} disabled={saving}>
            {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Create/Edit Group modal ─────────────────────────────────────────── */
const GROUP_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#10b981', '#06b6d4', '#f59e0b', '#ef4444'];

const GroupModal = ({ group, clubId, onClose, onSaved }) => {
  const { toast } = useToast();
  const [name, setName]   = useState(group?.name || '');
  const [color, setColor] = useState(group?.color || GROUP_COLORS[0]);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!name.trim()) { toast('Введите название', { type: 'warning' }); return; }
    setSaving(true);
    try {
      if (group) {
        await apiFetch(`/api/v1/computers/groups/${group.id}/`, { method: 'PATCH',
          body: JSON.stringify({ name: name.trim(), color }) });
        toast('Группа обновлена', { type: 'success' });
      } else {
        await apiFetch(`/api/v1/computers/groups/`, { method: 'POST',
          body: JSON.stringify({ name: name.trim(), color, club: Number(clubId) }) });
        toast('Группа создана', { type: 'success' });
      }
      onSaved();
    } catch (e) { toast(e.message, { type: 'error' }); }
    finally { setSaving(false); }
  };

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 14, width: 340,
        border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border-color)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>
            {group ? 'Редактировать группу' : 'Создать группу'}
          </h3>
          <button className="icon-btn" onClick={onClose}><X size={15} /></button>
        </div>
        <div style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 5 }}>
              Название <span style={{ float: 'right' }}>{name.length}/12</span>
            </label>
            <input value={name} onChange={e => setName(e.target.value.slice(0, 12))}
              placeholder="VIP зал"
              style={{ height: 38, padding: '0 12px', width: '100%', boxSizing: 'border-box',
                background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                borderRadius: 8, color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit' }} />
          </div>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 8 }}>
              Цвет
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              {GROUP_COLORS.map(c => (
                <div key={c} onClick={() => setColor(c)}
                  style={{ width: 28, height: 28, borderRadius: '50%', background: c, cursor: 'pointer',
                    border: color === c ? '3px solid var(--text-main)' : '3px solid transparent',
                    boxSizing: 'border-box' }} />
              ))}
            </div>
          </div>
          <button className="btn btn-primary" style={{ marginTop: 4 }} onClick={save} disabled={saving}>
            {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Tariff / Sale modal ─────────────────────────────────────────────── */
const TYPE_BADGE = {
  subscription: { label: 'Абонемент',     color: '#fb923c' },
  package:      { label: 'Пакет',         color: '#38bdf8' },
  per_minute:   { label: 'Поминутный',    color: '#a855f7' },
  fixed:        { label: 'Фиксированный', color: '#ec4899' },
};

const TariffModal = ({ pc, clubId, onClose, onSaved }) => {
  const { toast } = useToast();
  const [tariffs, setTariffs]   = useState([]);
  const [loadingT, setLoadingT] = useState(true);
  const [search, setSearch]     = useState('');
  const [tab, setTab]           = useState('tariffs');
  const [selected, setSelected] = useState(null);
  const [method, setMethod]     = useState('cash');
  const [saving, setSaving]     = useState(false);
  // client search
  const [clientQuery, setClientQuery]     = useState('');
  const [clientResults, setClientResults] = useState([]);
  const [client, setClient]               = useState(null);

  useEffect(() => {
    apiFetch(`/api/v1/billing/tariffs/?club=${clubId}`)
      .then(r => setTariffs(r.results || r || []))
      .catch(() => {})
      .finally(() => setLoadingT(false));
  }, [clubId]);

  // Debounced client search
  useEffect(() => {
    if (!clientQuery || clientQuery.length < 2) { setClientResults([]); return; }
    const t = setTimeout(async () => {
      try {
        const r = await apiFetch(`/api/v1/accounts/users/search/?q=${encodeURIComponent(clientQuery)}`);
        setClientResults(r.results || r || []);
      } catch { setClientResults([]); }
    }, 300);
    return () => clearTimeout(t);
  }, [clientQuery]);

  const price = (t) => parseFloat(t?.price) || 0;
  const fmtDuration = (min) => {
    if (!min) return '—';
    const h = Math.floor(min / 60), m = min % 60;
    return h > 0 ? `${h} ч${m > 0 ? ` ${m} мин` : ''}` : `${m} мин`;
  };
  const filtered = tariffs.filter(t => t.name?.toLowerCase().includes(search.toLowerCase()));

  const pay = async () => {
    if (!selected) { toast('Выберите тариф', { type: 'warning' }); return; }
    setSaving(true);
    try {
      await apiFetch('/api/v1/computers/admin/session/start/', {
        method: 'POST',
        body: JSON.stringify({
          computer_id: pc.id,
          tariff_id: selected.id,
          user_id: client?.id || null,
          payment_method: method === 'split' ? 'cash' : method,
          amount_paid: price(selected),
        }),
      });
      toast(`Сеанс на ${pc.name} начат`, { type: 'success' });
      onSaved();
    } catch (e) { toast(e.body?.error || e.message, { type: 'error' }); }
    finally { setSaving(false); }
  };

  const total = selected ? price(selected) : 0;
  const endTime = selected
    ? new Date(Date.now() + (selected.minutes || 0) * 60000).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    : '—';

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 16, width: 760,
        maxWidth: '94vw', maxHeight: '86vh', border: '1px solid var(--border-color)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border-color)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>Продажа · {pc.name}</h3>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>

        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left — items */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Client bar */}
            <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-color)', position: 'relative' }}>
              {client ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
                  background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: 8 }}>
                  <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 12 }}>
                    {(client.username || '?')[0].toUpperCase()}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{client.username}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{client.phone || client.full_name || ''}</div>
                  </div>
                  <button className="icon-btn" onClick={() => { setClient(null); setClientQuery(''); }}><X size={13} /></button>
                </div>
              ) : (
                <>
                  <div style={{ position: 'relative' }}>
                    <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                    <input value={clientQuery} onChange={e => setClientQuery(e.target.value)}
                      placeholder="Найти клиента (или оставьте — гость)"
                      style={{ paddingLeft: 32, height: 36, width: '100%', boxSizing: 'border-box',
                        background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: 8,
                        color: 'var(--text-main)', fontSize: 13, fontFamily: 'inherit' }} />
                  </div>
                  {clientResults.length > 0 && (
                    <div style={{ position: 'absolute', top: '100%', left: 20, right: 20, zIndex: 50,
                      background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 8,
                      boxShadow: '0 8px 24px rgba(0,0,0,0.4)', overflow: 'hidden', maxHeight: 200, overflowY: 'auto' }}>
                      {clientResults.map(u => (
                        <div key={u.id} onClick={() => { setClient(u); setClientResults([]); setClientQuery(''); }}
                          style={{ padding: '9px 12px', cursor: 'pointer', fontSize: 13 }}
                          onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                          <div style={{ fontWeight: 600 }}>{u.username}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{u.phone || u.full_name || ''}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Tabs + search */}
            <div style={{ padding: '12px 20px 0', display: 'flex', gap: 4, alignItems: 'center', flexShrink: 0 }}>
              {['tariffs', 'goods', 'services', 'combos'].map((t, i) => (
                <button key={t} onClick={() => setTab(t)}
                  style={{ padding: '7px 14px', borderRadius: 8, fontSize: 13, cursor: 'pointer', border: 'none', fontFamily: 'inherit', fontWeight: 500,
                    background: tab === t ? 'var(--accent)' : 'var(--hover-overlay)',
                    color: tab === t ? '#fff' : 'var(--text-muted)' }}>
                  {['Тарифы', 'Товары', 'Услуги', 'Комбо'][i]}
                </button>
              ))}
              <div style={{ flex: 1 }} />
              {tab === 'tariffs' && (
                <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Поиск"
                  style={{ height: 30, width: 130, padding: '0 10px', background: 'var(--bg-dark)',
                    border: '1px solid var(--border-color)', borderRadius: 8, color: 'var(--text-main)', fontSize: 12, fontFamily: 'inherit' }} />
              )}
            </div>

            {/* Cards list */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '14px 20px', display: 'flex', flexDirection: 'column', gap: 8 }}>
              {tab !== 'tariffs' ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                  Раздел «{{ goods: 'Товары', services: 'Услуги', combos: 'Комбо' }[tab]}» — добавьте позиции в разделе «Товары и услуги»
                </div>
              ) : loadingT ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>Загрузка тарифов…</div>
              ) : filtered.length === 0 ? (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                  Тарифов нет. Создайте в разделе «Тарифы».
                </div>
              ) : filtered.map(t => {
                const badge = TYPE_BADGE[t.tariff_type] || { label: t.tariff_type, color: '#6366f1' };
                const isSel = selected?.id === t.id;
                return (
                  <div key={t.id} onClick={() => setSelected(t)}
                    style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '12px 14px', borderRadius: 10, cursor: 'pointer',
                      border: `1.5px solid ${isSel ? badge.color : 'var(--border-color)'}`,
                      background: isSel ? `${badge.color}14` : 'var(--bg-dark)', transition: 'all 0.12s' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{t.name}</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 999,
                          background: `${badge.color}22`, color: badge.color, textTransform: 'uppercase' }}>{badge.label}</span>
                        <span style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Clock size={11} /> {t.hours_display || fmtDuration(t.minutes)}
                        </span>
                      </div>
                    </div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#10b981', whiteSpace: 'nowrap' }}>
                      {price(t) === 0 ? 'По факту' : `${price(t).toLocaleString('ru-RU')} сум`}
                    </div>
                    {isSel && <Check size={18} color={badge.color} />}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right — cart / pay */}
          <div style={{ width: 260, flexShrink: 0, borderLeft: '1px solid var(--border-color)',
            padding: 20, display: 'flex', flexDirection: 'column' }}>
            <div style={{ flex: 1 }}>
              {!selected ? (
                <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
                  Выберите тариф, чтобы добавить в корзину
                </div>
              ) : (
                <>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Корзина</div>
                  <div style={{ padding: 12, borderRadius: 10, background: 'var(--bg-dark)', marginBottom: 14 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{selected.name}</span>
                      <span style={{ fontWeight: 700, color: '#10b981' }}>{price(selected).toLocaleString('ru-RU')} сум</span>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{fmtDuration(selected.minutes)}</div>
                  </div>
                  <div style={{ fontSize: 12, display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ color: 'var(--text-muted)' }}>Клиент</span>
                    <span>{client?.username || 'Гость'}</span>
                  </div>
                  <div style={{ fontSize: 12, display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ color: 'var(--text-muted)' }}>Окончание</span><span>{endTime}</span>
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 700, display: 'flex', justifyContent: 'space-between',
                    borderTop: '1px solid var(--border-row)', paddingTop: 10, marginTop: 4 }}>
                    <span>Итого</span><span style={{ color: '#10b981' }}>{total.toLocaleString('ru-RU')} сум</span>
                  </div>
                </>
              )}
            </div>

            {/* Payment methods */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, margin: '14px 0' }}>
              {[['cash','💵 Наличные'],['card','💳 Карта'],['balance','🏦 Депозит'],['split','✂ Разделить']].map(([v,l]) => (
                <button key={v} onClick={() => setMethod(v)}
                  style={{ height: 40, fontSize: 11, fontWeight: 500, border: `1px solid ${method === v ? 'var(--accent)' : 'var(--border-color)'}`,
                    borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
                    background: method === v ? 'rgba(99,102,241,0.12)' : 'var(--bg-dark)',
                    color: method === v ? 'var(--accent)' : 'var(--text-muted)' }}>
                  {l}
                </button>
              ))}
            </div>
            <button className="btn btn-primary" style={{ width: '100%', height: 46, fontSize: 14, fontWeight: 600 }}
              onClick={pay} disabled={saving || !selected}>
              {saving ? 'Запуск…' : selected ? `Оплатить ${total.toLocaleString('ru-RU')} сум` : 'Оплатить'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ─── Main Computers component ────────────────────────────────────────── */
const Computers = () => {
  const { toast } = useToast();
  const [computers, setComputers] = useState([]);
  const [groups, setGroups]       = useState([]);
  const [loading, setLoading]     = useState(true);
  const [search, setSearch]       = useState('');
  const [view, setView]           = useState('table'); // 'table' | 'map'
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [activeGroup, setActiveGroup] = useState('all');
  const [activePc, setActivePc]   = useState(null);
  const [menu, setMenu]           = useState(null);   // { pc, x, y }
  const [modal, setModal]         = useState(null);   // { type, pc? }
  const [pcAction, setPcAction]   = useState(null);   // { mode, pc } → PcActionModal
  const [closePc, setClosePc]     = useState(null);   // postpaid PC pending close → ClosePostpaidModal

  const clubId = localStorage.getItem('active_club_id');

  /* ─── load ─── */
  const load = useCallback(async () => {
    if (!clubId) { setLoading(false); return; }
    try {
      const [pcsJson, grpJson] = await Promise.all([
        apiFetch(`/api/v1/computers/?club=${clubId}`).catch(() => []),
        apiFetch(`/api/v1/computers/groups/?club=${clubId}`).catch(() => []),
      ]);
      const pcs = pcsJson.results || pcsJson || [];
      const grps = grpJson.results || grpJson || [];
      setComputers(pcs);
      setGroups(grps);
      // keep active pc in sync
      if (activePc) {
        const updated = pcs.find(p => p.id === activePc.id);
        if (updated) setActivePc(updated);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [clubId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  /* ─── filter ─── */
  const filtered = useMemo(() => computers.filter(pc => {
    const matchGroup = activeGroup === 'all' || String(pc.group) === String(activeGroup);
    const q = search.toLowerCase();
    const matchSearch = !q
      || pc.name?.toLowerCase().includes(q)
      || (pc.active_session?.client || '').toLowerCase().includes(q)
      || String(pc.pc_number || '').includes(q);
    return matchGroup && matchSearch;
  }), [computers, search, activeGroup]);

  /* ─── stats ─── */
  const stats = useMemo(() => {
    const busy = computers.filter(p => p.active_session).length;
    const booked = computers.filter(p => !p.active_session && p.next_booking).length;
    const online = computers.filter(p => !p.active_session && !p.next_booking && p.status === 'ONLINE').length;
    const offline = computers.filter(p => p.status === 'OFFLINE' || p.status === 'DISABLED').length;
    const maintenance = computers.filter(p => p.status === 'MAINTENANCE').length;
    return { busy, booked, online, offline, maintenance };
  }, [computers]);

  /* ─── context menu action ─── */
  const handleAction = async (pcId, action) => {
    // Map UI actions → backend command_type values the model/shell actually support.
    // Включить = Wake-on-LAN, Выйти из системы = lock (закрыть доступ → экран входа).
    const cmdMap = {
      reboot: 'reboot', shutdown: 'shutdown', logout_os: 'lock',
      wake: 'wol', lock: 'lock', unlock: 'unlock',
    };
    if (action === 'stop_session') {
      // For a postpaid PC, open the close dialog so the cashier sees the amount due
      // and picks a payment method before billing. Plain sessions close directly.
      const pc = computers.find(c => String(c.id) === String(pcId));
      if (pc?.active_session?.is_postpaid) { setClosePc(pc); return; }
      try {
        const res = await apiFetch('/api/v1/computers/admin/session/stop/', {
          method: 'POST', body: JSON.stringify({ computer_id: pcId }),
        });
        toast(res?.message || 'Сеанс завершён', { type: 'success' });
        await load();
      } catch (e) {
        toast(e.body ? Object.values(e.body).flat().join(', ') : (e.message || 'Ошибка'), { type: 'error' });
      }
      return;
    }
    if (action === 'delete') {
      if (!window.confirm('Удалить ПК?')) return;
      try {
        await apiFetch(`/api/v1/computers/${pcId}/`, { method: 'DELETE' });
        toast('ПК удалён', { type: 'success' });
        if (activePc?.id === pcId) setActivePc(null);
        await load();
      } catch (e) { toast(e.message, { type: 'error' }); }
      return;
    }
    if (action === 'high_access') {
      // Toggle elevated desktop access on this PC (grant = drop kiosk + restore shell).
      const pc = computers.find(c => String(c.id) === String(pcId));
      const enable = !(pc?.high_access_active);
      if (!window.confirm(enable
        ? 'Включить высокий доступ (полный доступ к рабочему столу) на этом ПК?'
        : 'Выключить высокий доступ и вернуть киоск-режим?')) return;
      try {
        const res = await apiFetch(`/api/v1/computers/${pcId}/high-access/`, {
          method: 'POST', body: JSON.stringify({ enabled: enable }),
        });
        toast(res?.message || 'Готово', { type: 'success' });
        await load();
      } catch (e) {
        toast(e.body ? Object.values(e.body).flat().join(', ') : (e.message || 'Ошибка'), { type: 'error' });
      }
      return;
    }
    if (action === 'client_arrived') {
      // BUGFIX: was a dead no-op — mark the PC's active booking REDEEMED so the
      // no-show sweep doesn't cancel it and the slot is freed.
      try {
        const res = await apiFetch('/api/v1/bookings/redeem/', {
          method: 'POST', body: JSON.stringify({ computer_id: pcId }),
        });
        toast(res?.success ? 'Бронь отмечена — клиент пришёл' : 'Готово', { type: 'success' });
        await load();
      } catch (e) {
        toast(e.body ? Object.values(e.body).flat().join(', ') : (e.message || 'Активная бронь не найдена'), { type: 'error' });
      }
      return;
    }
    if (action.startsWith('fine_')) {
      const min = parseInt(action.split('_')[1]);
      // BUGFIX: was POSTing command_type:'fine' with key 'computer' → backend 400
      // (no such CommandType, wrong key) and the shell had no handler. A penalty is an
      // authoritative time deduction, so hit the dedicated billing endpoint instead.
      try {
        const res = await apiFetch('/api/v1/computers/admin/session/fine/', {
          method: 'POST', body: JSON.stringify({ computer_id: pcId, minutes: min }),
        });
        toast(`Штраф ${min} мин. Осталось: ${res?.minutes_remaining ?? '—'} мин`, { type: 'success' });
        await load();
      } catch (e) {
        toast(e.body ? Object.values(e.body).flat().join(', ') : (e.message || 'Ошибка'), { type: 'error' });
      }
      return;
    }
    if (cmdMap[action]) {
      try {
        await apiFetch('/api/v1/computers/admin/commands/', {
          method: 'POST', body: JSON.stringify({ computer_id: pcId, command_type: cmdMap[action] }),
        });
        toast(`Команда отправлена`, { type: 'success' });
      } catch (e) {
        toast(e.body ? Object.values(e.body).flat().join(', ') : (e.message || 'Ошибка'), { type: 'error' });
      }
      return;
    }
    // Actions handled by the universal PcActionModal (postpaid / deposit / move / booking)
    const modalModes = { postpay: 'postpay', deposit: 'topup', move: 'transfer', book: 'booking' };
    if (modalModes[action]) {
      const pc = computers.find(c => String(c.id) === String(pcId));
      if (pc) { setPcAction({ mode: modalModes[action], pc }); return; }
    }
    toast(`${action}`, { type: 'info' });
  };

  /* ─── send notification ─── */
  const sendNotif = async (text) => {
    if (!modal?.pc || !text.trim()) { toast('Введите текст', { type: 'warning' }); return; }
    try {
      const res = await apiFetch('/api/v1/computers/admin/notify/', {
        method: 'POST',
        body: JSON.stringify({ computer_id: modal.pc.id, text }),
      });
      toast(res?.message || 'Уведомление отправлено', { type: res?.delivered ? 'success' : 'warning' });
      setModal(null);
    } catch (e) {
      toast(e.body ? Object.values(e.body).flat().join(', ') : (e.message || 'Ошибка'), { type: 'error' });
    }
  };

  /* ─── selection helpers ─── */
  const toggleId = (id) => setSelectedIds(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const toggleGroup = (ids) => setSelectedIds(p => {
    const n = new Set(p);
    const allIn = ids.every(id => n.has(id));
    ids.forEach(id => allIn ? n.delete(id) : n.add(id));
    return n;
  });
  const toggleAll = () => {
    if (selectedIds.size === filtered.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(filtered.map(p => p.id)));
  };

  const openCtx = (e, pc) => {
    e.preventDefault();
    setMenu({ pc, x: e.clientX, y: e.clientY });
  };

  const selectPc = (pc) => setActivePc(prev => prev?.id === pc.id ? null : pc);

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* ─── Toolbar ─── */}
        <div style={{ padding: '0 24px', marginBottom: 12, display: 'flex',
          gap: 10, alignItems: 'center', flexWrap: 'wrap', flexShrink: 0 }}>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700 }}>Компьютеры</h2>

          {/* Stats */}
          <div style={{ display: 'flex', gap: 5, marginLeft: 6 }}>
            {[
              { key: 'busy',        label: 'Занято',       color: '#6366f1' },
              { key: 'online',      label: 'Свободно',     color: '#10b981' },
              { key: 'offline',     label: 'Выключено',    color: '#6b7280' },
              { key: 'maintenance', label: 'Обслуживание', color: '#f59e0b' },
            ].map(({ key, label, color }) => (
              <span key={key} style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '999px',
                background: 'var(--hover-overlay)', color: 'var(--text-muted)',
                display: 'flex', alignItems: 'center', gap: 4 }}>
                <Circle size={6} fill={color} stroke="none" />
                {stats[key]} {label}
              </span>
            ))}
          </div>

          <div style={{ flex: 1 }} />

          {/* Search */}
          <div style={{ position: 'relative' }}>
            <Search size={13} style={{ position: 'absolute', left: 10, top: '50%',
              transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Поиск ПК или клиента…"
              style={{ paddingLeft: 30, paddingRight: 12, height: 34, width: 210,
                background: 'var(--bg-input)', border: '1px solid var(--border-input)',
                borderRadius: 8, color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit' }} />
          </div>

          {/* View toggle */}
          <div style={{ display: 'flex', border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
            {[['table', <List size={14} />], ['map', <Map size={14} />]].map(([v, icon]) => (
              <button key={v} onClick={() => setView(v)}
                style={{ width: 36, height: 34, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  border: 'none', cursor: 'pointer', fontFamily: 'inherit',
                  background: view === v ? 'var(--accent)' : 'var(--bg-dark)',
                  color: view === v ? '#fff' : 'var(--text-muted)' }}>
                {icon}
              </button>
            ))}
          </div>

          <button className="btn btn-secondary" onClick={load} disabled={loading}><RefreshCw size={14} /></button>
          <button className="btn btn-secondary" onClick={() => setModal({ type: 'group' })}
            style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '13px' }}>
            <Plus size={13} /> Группа
          </button>
          <button className="btn btn-primary" onClick={() => setModal({ type: 'pc' })}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Plus size={13} /> Создать ПК
          </button>
        </div>

        {/* ─── Group filter tabs ─── */}
        {groups.length > 0 && (
          <div style={{ padding: '0 24px', marginBottom: 12, display: 'flex', gap: 5, overflowX: 'auto', flexShrink: 0 }}>
            {[{ id: 'all', name: 'Все зоны' }, ...groups].map(g => (
              <button key={g.id} onClick={() => setActiveGroup(g.id)}
                style={{ padding: '5px 13px', borderRadius: 8, fontSize: '12px', fontWeight: 500,
                  cursor: 'pointer', fontFamily: 'inherit', border: 'none', whiteSpace: 'nowrap',
                  background: activeGroup === g.id ? 'var(--accent)' : 'var(--hover-overlay)',
                  color: activeGroup === g.id ? '#fff' : 'var(--text-muted)' }}>
                {g.id !== 'all' && g.color && (
                  <span style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%',
                    background: g.color, marginRight: 5, verticalAlign: 'middle' }} />
                )}
                {g.name}
              </button>
            ))}
          </div>
        )}

        {/* ─── Bulk bar ─── */}
        {selectedIds.size > 1 && (
          <div style={{ margin: '0 24px 10px', padding: '9px 16px',
            background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)',
            borderRadius: 10, display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
            <span style={{ fontSize: '13px', color: '#818cf8' }}>Выбрано: <b>{selectedIds.size}</b> ПК</span>
            <button className="btn btn-secondary" style={{ fontSize: '12px', padding: '4px 10px' }}
              onClick={() => toast('Массовое уведомление', { type: 'info' })}>
              <Send size={12} /> Уведомление
            </button>
            <button className="btn btn-secondary" style={{ fontSize: '12px', padding: '4px 10px' }}
              onClick={() => toast('Перезагрузка…', { type: 'info' })}>
              <RefreshCw size={12} /> Перезагрузить
            </button>
            <button className="icon-btn" onClick={() => setSelectedIds(new Set())}><X size={13} /></button>
          </div>
        )}

        {/* ─── Content ─── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 24px 16px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
              Загрузка компьютеров…
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)',
              background: 'var(--bg-panel)', borderRadius: 12, border: '1px solid var(--border-color)' }}>
              <Monitor size={36} style={{ marginBottom: 12, opacity: 0.3 }} />
              <div>Компьютеры не найдены</div>
            </div>
          ) : view === 'table' ? (
            <TableView
              groups={groups}
              computers={filtered}
              selectedIds={selectedIds}
              allFilteredIds={filtered.map(p => p.id)}
              onToggle={toggleId}
              onToggleGroup={toggleGroup}
              onToggleAll={toggleAll}
              onContextMenu={openCtx}
              onSelectPc={selectPc}
              activePcId={activePc?.id}
            />
          ) : (
            <MapView
              groups={groups}
              computers={filtered}
              selectedIds={selectedIds}
              activePcId={activePc?.id}
              onSelectPc={selectPc}
              onContextMenu={openCtx}
            />
          )}
        </div>
      </div>

      {/* ─── Right detail panel ─── */}
      {activePc && (
        <PcDetailPanel
          pc={activePc}
          onClose={() => setActivePc(null)}
          onAction={handleAction}
          onOpenNotif={(pc) => setModal({ type: 'notif', pc })}
          onOpenTariff={(pc) => setModal({ type: 'tariff', pc })}
        />
      )}

      {/* ─── Context menu ─── */}
      {menu && (
        <ContextMenu
          pc={menu.pc} x={menu.x} y={menu.y}
          onClose={() => setMenu(null)}
          onAction={handleAction}
          onOpenNotif={(pc) => setModal({ type: 'notif', pc })}
          onOpenEdit={(pc) => setModal({ type: 'editpc', pc })}
          onOpenTariff={(pc) => setModal({ type: 'tariff', pc })}
        />
      )}

      {/* ─── Modals ─── */}
      {modal?.type === 'notif' && (
        <NotifModal pc={modal.pc} onClose={() => setModal(null)} onSend={sendNotif} />
      )}
      {modal?.type === 'tariff' && (
        <TariffModal pc={modal.pc} clubId={clubId} onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }} />
      )}
      {(modal?.type === 'pc' || modal?.type === 'editpc') && (
        <EditPcModal pc={modal.pc || null} groups={groups} clubId={clubId}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }} />
      )}
      {modal?.type === 'group' && (
        <GroupModal group={modal.group || null} clubId={clubId}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }} />
      )}

      {/* Universal PC action modal — postpaid / deposit / move / booking */}
      <PcActionModal
        mode={pcAction?.mode}
        pc={pcAction?.pc}
        isOpen={!!pcAction}
        onClose={() => setPcAction(null)}
        onDone={() => { setPcAction(null); load(); }} />

      {/* Close postpaid: amount due + payment method */}
      {closePc && (
        <ClosePostpaidModal
          pc={closePc}
          onClose={() => setClosePc(null)}
          onDone={() => { setClosePc(null); load(); }} />
      )}
    </div>
  );
};

export default Computers;
