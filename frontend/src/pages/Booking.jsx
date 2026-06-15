import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Calendar, Plus, RefreshCw, X, Trash2, ChevronDown, Search, User } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

/* ─── constants ─────────────────────────────────────────────────────── */
const SLOT_W = 56;  // px per 30-minute slot
const SLOTS  = 48;  // 00:00–23:30

const BOOKING_COLORS = {
  active:   { bg: 'rgba(99,102,241,0.85)',  border: '#6366f1', text: '#fff' },
  guest:    { bg: 'rgba(167,139,250,0.80)', border: '#a78bfa', text: '#fff' },
  finished: { bg: 'rgba(100,116,139,0.50)', border: '#64748b', text: '#94a3b8' },
  canceled: { bg: 'rgba(239,68,68,0.30)',   border: '#ef4444', text: '#fca5a5' },
};

/* ─── helpers ────────────────────────────────────────────────────────── */
const dateStr = (d) => {
  const dt = d instanceof Date ? d : new Date(d);
  return dt.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

const timeStr = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }); }
  catch { return '—'; }
};

// LOCAL YYYY-MM-DD for <input type=date> — must share the same local base as
// timeStr(), otherwise the edit modal mixes a UTC date with a local time and
// shifts near-midnight bookings.
const dateInputStr = (d) => {
  const x = (d instanceof Date) ? d : new Date(d);
  const p = (n) => String(n).padStart(2, '0');
  return `${x.getFullYear()}-${p(x.getMonth() + 1)}-${p(x.getDate())}`;
};

const minutesFromMidnight = (iso) => {
  const d = new Date(iso);
  return d.getHours() * 60 + d.getMinutes();
};

const durationHours = (from, to) => {
  if (!from || !to) return 0;
  return Math.max(0, (new Date(to) - new Date(from)) / 3_600_000);
};

const iStyle = {
  height: '36px', padding: '0 10px', width: '100%',
  background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
  borderRadius: '8px', color: 'var(--text-main)', fontSize: '13px',
  fontFamily: 'inherit',
};

/* ─── ClientSearchInput ──────────────────────────────────────────────── */
const ClientSearchInput = ({ value, onChange, clubId }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const ref = useRef();
  const timer = useRef();

  const handleInput = (e) => {
    const q = e.target.value;
    setQuery(q);
    clearTimeout(timer.current);
    if (!q.trim()) { setResults([]); setOpen(false); return; }
    timer.current = setTimeout(async () => {
      try {
        const r = await apiFetch(`/api/v1/billing/admin/users/?search=${encodeURIComponent(q)}&club=${clubId}`);
        setResults((r.results || r || []).slice(0, 8));
        setOpen(true);
      } catch { setResults([]); }
    }, 280);
  };

  const select = (u) => {
    onChange({ id: u.id, label: u.username || u.phone || `#${u.id}`, phone: u.phone });
    setQuery(u.username || u.phone || '');
    setOpen(false);
  };

  // close on outside click
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div style={{ position: 'relative' }}>
        <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
        <input value={value?.label ? value.label : query} onChange={handleInput}
          onFocus={() => query && setOpen(true)}
          placeholder="Найти клиента (никнейм или телефон)"
          style={{ ...iStyle, paddingLeft: 32 }} />
      </div>
      {open && results.length > 0 && (
        <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 200,
          background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
          borderRadius: '8px', overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.4)', marginTop: 2 }}>
          {results.map(u => (
            <div key={u.id} onMouseDown={() => select(u)}
              style={{ padding: '9px 14px', cursor: 'pointer', fontSize: '13px',
                display: 'flex', gap: '8px', alignItems: 'center' }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <User size={13} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              <span style={{ fontWeight: 500 }}>{u.username}</span>
              {u.phone && <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>{u.phone}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/* ─── BookingModal (create + edit) ──────────────────────────────────── */
const BookingModal = ({ mode, booking, bookings, pcs, clubId, onClose, onSaved }) => {
  const { toast } = useToast();
  const [saving, setSaving] = useState(false);
  const [client, setClient] = useState(booking?.client ? { id: booking.client, label: booking.client_username || '' } : null);
  const [guestName, setGuestName] = useState(booking?.guest_name || '');
  const [guestPhone, setGuestPhone] = useState(booking?.guest_phone || '');
  const [date, setDate] = useState(
    booking ? dateInputStr(booking.from_at) : dateInputStr(new Date())
  );
  const [startTime, setStartTime] = useState(
    booking ? timeStr(booking.from_at).replace(':', ':') : '20:00'
  );
  const [duration, setDuration] = useState(
    booking ? Math.round(durationHours(booking.from_at, booking.to_at)) || 2 : 2
  );
  const [selectedPcs, setSelectedPcs] = useState(booking?.hosts || []);
  const [comment, setComment] = useState(booking?.comment || '');

  // Calculate from_at / to_at from date + startTime + duration
  const fromDt = useMemo(() => {
    try { return new Date(`${date}T${startTime}:00`); } catch { return null; }
  }, [date, startTime]);

  const toDt = useMemo(() => {
    if (!fromDt) return null;
    return new Date(fromDt.getTime() + duration * 3_600_000);
  }, [fromDt, duration]);

  // Check PC availability
  const pcAvailability = useMemo(() => {
    const map = {};
    pcs.forEach(pc => {
      const conflict = bookings.filter(b =>
        b.id !== booking?.id &&
        b.status === 'active' &&
        b.hosts?.includes(pc.id) &&
        fromDt && toDt &&
        new Date(b.from_at) < toDt &&
        new Date(b.to_at) > fromDt
      );
      map[pc.id] = conflict.length === 0 ? 'free' : 'busy';
    });
    return map;
  }, [pcs, bookings, fromDt, toDt, booking]);

  const togglePc = (id) => {
    if (pcAvailability[id] === 'busy') return;
    setSelectedPcs(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const selectedPcObjects = pcs.filter(p => selectedPcs.includes(p.id));

  const save = async () => {
    if (!fromDt || !toDt) { toast('Укажите дату и время', { type: 'warning' }); return; }
    if (selectedPcs.length === 0) { toast('Выберите хотя бы один ПК', { type: 'warning' }); return; }
    setSaving(true);
    try {
      const body = {
        club: Number(clubId),
        hosts: selectedPcs,
        from_at: fromDt.toISOString(),
        to_at: toDt.toISOString(),
        comment,
        ...(client ? { client: client.id } : { guest_name: guestName, guest_phone: guestPhone }),
      };
      if (mode === 'edit') {
        await apiFetch(`/api/v1/bookings/${booking.id}/`, { method: 'PATCH', body: JSON.stringify(body) });
        toast('Бронь обновлена', { type: 'success' });
      } else {
        await apiFetch('/api/v1/bookings/', { method: 'POST', body: JSON.stringify(body) });
        toast('Бронь создана', { type: 'success' });
      }
      onSaved();
      onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка', { type: 'error' });
    } finally { setSaving(false); }
  };

  const del = async () => {
    if (!window.confirm('Отменить бронь?')) return;
    setSaving(true);
    try {
      await apiFetch(`/api/v1/bookings/${booking.id}/`, { method: 'PATCH', body: JSON.stringify({ status: 'canceled' }) });
      toast('Бронь отменена', { type: 'success' });
      onSaved(); onClose();
    } catch (e) { toast(e.message, { type: 'error' }); }
    finally { setSaving(false); }
  };

  // Group PCs by group for display
  const pcGroups = useMemo(() => {
    const groups = {};
    pcs.forEach(pc => {
      const g = pc.group_name || 'Общий зал';
      if (!groups[g]) groups[g] = [];
      groups[g].push(pc);
    });
    return groups;
  }, [pcs]);

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: '14px',
        width: '900px', maxWidth: '95vw', maxHeight: '90vh',
        border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border-color)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>
            {mode === 'edit' ? 'Редактирование брони' : 'Создание брони'}
          </h3>
          <button className="icon-btn" onClick={onClose}><X size={16} /></button>
        </div>

        {/* Body: 3 columns */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 280px', overflow: 'hidden', flex: 1 }}>

          {/* Left — client + datetime */}
          <div style={{ padding: '20px', borderRight: '1px solid var(--border-color)', overflowY: 'auto' }}>
            <div style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '6px' }}>Клиент</label>
              <ClientSearchInput value={client} onChange={setClient} clubId={clubId} />
              {!client && (
                <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <input value={guestName} onChange={e => setGuestName(e.target.value)}
                    placeholder="Имя гостя" style={iStyle} />
                  <input value={guestPhone} onChange={e => setGuestPhone(e.target.value)}
                    placeholder="Телефон" style={iStyle} />
                </div>
              )}
              {client && (
                <button onClick={() => setClient(null)}
                  style={{ marginTop: '6px', fontSize: '11px', color: 'var(--text-muted)',
                    background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                  ✕ Убрать клиента (бронь как гость)
                </button>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '5px' }}>Дата брони</label>
                <input type="date" value={date} onChange={e => setDate(e.target.value)} style={iStyle} />
              </div>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '5px' }}>Начало</label>
                <input type="time" value={startTime} onChange={e => setStartTime(e.target.value)} style={iStyle} />
              </div>
            </div>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '5px' }}>Время, ч.</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button className="icon-btn" onClick={() => setDuration(d => Math.max(1, d - 1))}
                  style={{ width: 32, height: 32, fontSize: '18px' }}>−</button>
                <span style={{ fontWeight: 700, fontSize: '22px', minWidth: 32, textAlign: 'center' }}>{duration}</span>
                <button className="icon-btn" onClick={() => setDuration(d => d + 1)}
                  style={{ width: 32, height: 32, fontSize: '18px' }}>+</button>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {startTime} → {toDt ? toDt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '—'}
                </span>
              </div>
            </div>

            <div>
              <label style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '5px' }}>Дополнительная информация</label>
              <textarea value={comment} onChange={e => setComment(e.target.value)}
                rows={3} placeholder="Комментарий к брони…"
                style={{ ...iStyle, height: 'auto', padding: '10px 12px', resize: 'vertical', fontFamily: 'inherit' }} />
            </div>
          </div>

          {/* Middle — PC list */}
          <div style={{ padding: '20px', borderRight: '1px solid var(--border-color)', overflowY: 'auto' }}>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: '10px' }}>
              Выберите ПК
            </label>
            {Object.entries(pcGroups).map(([groupName, groupPcs]) => (
              <div key={groupName} style={{ marginBottom: '14px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600,
                  marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {groupName}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  {groupPcs.map(pc => {
                    const avail = pcAvailability[pc.id];
                    const sel = selectedPcs.includes(pc.id);
                    const busy = avail === 'busy';
                    return (
                      <button key={pc.id} onClick={() => togglePc(pc.id)} disabled={busy}
                        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                          padding: '9px 12px', borderRadius: '8px', cursor: busy ? 'not-allowed' : 'pointer',
                          fontFamily: 'inherit', fontSize: '13px', fontWeight: 500,
                          background: sel ? 'rgba(99,102,241,0.20)' : busy ? 'rgba(255,255,255,0.02)' : 'rgba(255,255,255,0.04)',
                          border: `1px solid ${sel ? '#6366f1' : 'var(--border-color)'}`,
                          color: busy ? 'var(--text-muted)' : 'var(--text-main)', opacity: busy ? 0.5 : 1 }}>
                        <span>{pc.name}</span>
                        <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '999px',
                          background: busy ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)',
                          color: busy ? '#ef4444' : '#10b981', fontWeight: 600 }}>
                          {busy ? 'Занят' : 'Свободен'}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Right — summary + actions */}
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', overflowY: 'auto', background: 'rgba(255,255,255,0.02)' }}>
            {selectedPcObjects.length > 0 ? (
              <>
                {selectedPcObjects.map(pc => (
                  <div key={pc.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    marginBottom: '8px', padding: '8px 10px', background: 'var(--hover-overlay)', borderRadius: '8px' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px' }}>{pc.name}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{pc.group_name || 'Общий зал'}</div>
                    </div>
                    <button className="icon-btn" style={{ width: 20, height: 20 }}
                      onClick={() => togglePc(pc.id)}><X size={12} /></button>
                  </div>
                ))}

                <div style={{ margin: '12px 0', borderTop: '1px solid var(--border-row)' }} />

                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '13px', flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Начало брони</span>
                    <span style={{ fontWeight: 500 }}>{fromDt ? dateStr(fromDt) + ' ' + startTime : '—'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Конец брони</span>
                    <span style={{ fontWeight: 500 }}>
                      {toDt ? dateStr(toDt) + ' ' + toDt.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '—'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Длительность</span>
                    <span style={{ fontWeight: 600 }}>{duration} ч.</span>
                  </div>
                  {(client || guestName) && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Клиент</span>
                      <span style={{ fontWeight: 500 }}>{client?.label || guestName}</span>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '20px' }}>
                Выберите ПК<br />из списка
              </div>
            )}

            <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {mode === 'edit' && (
                <button className="btn" onClick={del} disabled={saving}
                  style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)',
                    color: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
                  <Trash2 size={14} /> Отменить бронь
                </button>
              )}
              <button className="btn btn-primary" onClick={save} disabled={saving || selectedPcs.length === 0}>
                {saving ? 'Сохранение…' : mode === 'edit' ? 'Обновить' : 'Забронировать'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ─── GanttTimeline ──────────────────────────────────────────────────── */
const GanttTimeline = ({ pcs, bookings, selectedDate, onEdit, onCreateAt }) => {
  const scrollRef = useRef();
  const now = new Date();
  const todayStr = now.toISOString().slice(0, 10);
  const isToday = selectedDate === todayStr;
  const currentMinute = now.getHours() * 60 + now.getMinutes();
  const currentX = (currentMinute / 30) * SLOT_W;

  // Auto-scroll to current time (or start of day)
  useEffect(() => {
    if (scrollRef.current) {
      const scrollTo = isToday ? Math.max(0, currentX - 120) : 0;
      scrollRef.current.scrollLeft = scrollTo;
    }
  }, [selectedDate, isToday, currentX]);

  // Group PCs by group
  const pcGroups = useMemo(() => {
    const groups = {};
    pcs.forEach(pc => {
      const g = pc.group_name || 'Общий зал';
      if (!groups[g]) groups[g] = [];
      groups[g].push(pc);
    });
    return groups;
  }, [pcs]);

  // Filter bookings for selected date (exclude canceled — slot should appear free)
  const dayBookings = useMemo(() => {
    return bookings.filter(b => {
      // BUGFIX: compare the booking's LOCAL date, not its UTC date prefix — block
      // positioning uses local getHours(), so a UTC-date bucket put 23:00-local
      // bookings (UTC+5 → previous UTC day) in the wrong column / made them vanish.
      if (!b.from_at) return false;
      const d = new Date(b.from_at).toLocaleDateString('sv-SE'); // YYYY-MM-DD local
      return d === selectedDate && b.status !== 'canceled';
    });
  }, [bookings, selectedDate]);

  const getBookingsForPc = (pcId) =>
    dayBookings.filter(b => b.hosts?.includes(pcId));

  const LEFT_W = 160; // width of PC name column

  return (
    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
      borderRadius: '12px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>

      {/* Sticky header row */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', flexShrink: 0 }}>
        <div style={{ width: LEFT_W, flexShrink: 0, padding: '10px 14px',
          fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600,
          borderRight: '1px solid var(--border-color)', textTransform: 'uppercase' }}>
          Список хостов
        </div>
        <div ref={scrollRef} style={{ overflowX: 'auto', flex: 1 }}
          id="gantt-scroll">
          <div style={{ width: SLOTS * SLOT_W, display: 'flex', position: 'relative' }}>
            {Array.from({ length: SLOTS }).map((_, i) => {
              const h = Math.floor(i / 2).toString().padStart(2, '0');
              const m = i % 2 === 0 ? '00' : '30';
              const showLabel = i % 2 === 0;
              return (
                <div key={i} style={{ width: SLOT_W, flexShrink: 0,
                  borderRight: '1px solid rgba(255,255,255,0.04)',
                  padding: '8px 0 6px', textAlign: 'center' }}>
                  {showLabel && (
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{h}:{m}</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* PC rows */}
      <div style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 260px)' }}>
        {Object.entries(pcGroups).map(([groupName, groupPcs]) => (
          <div key={groupName}>
            {/* Group header */}
            <div style={{ padding: '6px 14px', background: 'rgba(255,255,255,0.02)',
              fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600,
              textTransform: 'uppercase', letterSpacing: '0.05em',
              borderBottom: '1px solid var(--border-color)', display: 'flex' }}>
              <span style={{ width: LEFT_W, flexShrink: 0 }}>● {groupName}</span>
            </div>

            {groupPcs.map((pc, idx) => {
              const pcBookings = getBookingsForPc(pc.id);
              return (
                <div key={pc.id} style={{
                  display: 'flex', alignItems: 'stretch',
                  borderBottom: idx < groupPcs.length - 1 ? '1px solid rgba(255,255,255,0.03)' : '1px solid var(--border-color)',
                  minHeight: 44,
                }}>
                  {/* PC name */}
                  <div style={{ width: LEFT_W, flexShrink: 0, padding: '8px 14px',
                    borderRight: '1px solid var(--border-color)', display: 'flex',
                    flexDirection: 'column', justifyContent: 'center' }}>
                    <div style={{ fontWeight: 600, fontSize: '13px' }}>{pc.name}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{pc.group_name || 'Общий зал'}</div>
                  </div>

                  {/* Timeline area — synced scroll with header */}
                  <div style={{ flex: 1, overflowX: 'hidden', position: 'relative', minHeight: 44 }}
                    id={`gantt-row-${pc.id}`}>
                    <div style={{ width: SLOTS * SLOT_W, position: 'relative', height: '100%', minHeight: 44 }}>
                      {/* Slot grid lines */}
                      {Array.from({ length: SLOTS }).map((_, i) => (
                        <div key={i} style={{ position: 'absolute', left: i * SLOT_W, top: 0, bottom: 0,
                          borderRight: i % 2 === 0
                            ? '1px solid rgba(255,255,255,0.04)'
                            : '1px dashed rgba(255,255,255,0.02)',
                          width: SLOT_W }} />
                      ))}

                      {/* Current time line */}
                      {isToday && (
                        <div style={{ position: 'absolute', left: currentX, top: 0, bottom: 0,
                          width: 2, background: '#6366f1', zIndex: 10, opacity: 0.8 }} />
                      )}

                      {/* Booking blocks */}
                      {pcBookings.map(b => {
                        const fromMin = minutesFromMidnight(b.from_at);
                        const toMin = minutesFromMidnight(b.to_at);
                        const dur = toMin > fromMin ? toMin - fromMin : 1440 - fromMin + toMin;
                        const left = (fromMin / 30) * SLOT_W;
                        const width = Math.max((dur / 30) * SLOT_W - 4, 20);
                        const isGuest = !b.client_username && b.guest_name;
                        const col = b.status === 'canceled' ? BOOKING_COLORS.canceled
                          : b.status === 'finished' ? BOOKING_COLORS.finished
                          : isGuest ? BOOKING_COLORS.guest
                          : BOOKING_COLORS.active;

                        return (
                          <div key={b.id}
                            onClick={() => onEdit(b)}
                            title={`${b.client_username || b.guest_name || 'Гость'} ${timeStr(b.from_at)}–${timeStr(b.to_at)}`}
                            style={{
                              position: 'absolute', left: left + 2, top: 4,
                              width, height: 'calc(100% - 8px)', minHeight: 32,
                              background: col.bg, border: `1px solid ${col.border}`,
                              borderRadius: 6, cursor: 'pointer', overflow: 'hidden',
                              zIndex: 5, padding: '2px 6px',
                              display: 'flex', flexDirection: 'column', justifyContent: 'center',
                            }}>
                            <div style={{ fontSize: '11px', fontWeight: 600, color: col.text,
                              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {b.client_username || b.guest_name || 'Гость'}
                            </div>
                            <div style={{ fontSize: '10px', color: col.text, opacity: 0.8 }}>
                              {timeStr(b.from_at)} — {timeStr(b.to_at)}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ))}

        {pcs.length === 0 && (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Нет ПК — добавьте компьютеры в разделе «Компьютеры»
          </div>
        )}
      </div>
    </div>
  );
};

/* ─── Sync horizontal scroll across all rows ─────────────────────────── */
const useSyncScroll = (pcs) => {
  useEffect(() => {
    const header = document.getElementById('gantt-scroll');
    if (!header) return;
    const rows = pcs.map(pc => document.getElementById(`gantt-row-${pc.id}`)).filter(Boolean);
    const onHeaderScroll = () => rows.forEach(r => { r.scrollLeft = header.scrollLeft; });
    header.addEventListener('scroll', onHeaderScroll);
    return () => header.removeEventListener('scroll', onHeaderScroll);
  }, [pcs]);
};

/* ─── Main Booking page ──────────────────────────────────────────────── */
const Booking = () => {
  const [bookings, setBookings] = useState([]);
  const [pcs, setPcs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // null | { mode: 'create' | 'edit', booking? }
  const [selectedDate, setSelectedDate] = useState(new Date().toLocaleDateString('sv-SE')); // local YYYY-MM-DD
  const [zoneFilter, setZoneFilter] = useState('all');
  const { toast } = useToast();
  const clubId = localStorage.getItem('active_club_id');

  useSyncScroll(pcs);

  const load = useCallback(async () => {
    if (!clubId) return;
    setLoading(true);
    try {
      const [bJson, pcJson] = await Promise.all([
        apiFetch(`/api/v1/bookings/?club=${clubId}`),
        apiFetch(`/api/v1/computers/?club=${clubId}`),
      ]);
      setBookings(bJson.results || bJson || []);
      setPcs(pcJson.results || pcJson || []);
    } catch (e) {
      toast('Ошибка загрузки: ' + e.message, { type: 'error' });
    } finally {
      setLoading(false);
    }
  }, [clubId]);

  useEffect(() => { load(); }, [load]);

  // Zone filter
  const zones = useMemo(() => {
    const s = new Set(pcs.map(pc => pc.group_name || 'Общий зал'));
    return ['all', ...s];
  }, [pcs]);

  const filteredPcs = useMemo(() =>
    zoneFilter === 'all' ? pcs : pcs.filter(p => (p.group_name || 'Общий зал') === zoneFilter),
    [pcs, zoneFilter]);

  const activeBookings = bookings.filter(b => b.status === 'active');
  const todayBookings = bookings.filter(b =>
    b.from_at?.slice(0, 10) === selectedDate && b.status !== 'canceled');

  return (
    <div style={{ padding: '0 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
        <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Calendar size={20} /> Бронирование
        </h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Date picker */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px',
            background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
            borderRadius: '8px', padding: '0 10px', height: '36px' }}>
            <Calendar size={13} style={{ color: 'var(--text-muted)' }} />
            <input type="date" value={selectedDate}
              onChange={e => setSelectedDate(e.target.value)}
              style={{ background: 'none', border: 'none', color: 'var(--text-main)',
                fontSize: '13px', fontFamily: 'inherit', outline: 'none', cursor: 'pointer' }} />
          </div>

          {/* Zone filter */}
          <div style={{ position: 'relative' }}>
            <select value={zoneFilter} onChange={e => setZoneFilter(e.target.value)}
              style={{ height: '36px', padding: '0 30px 0 10px',
                background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
                borderRadius: '8px', color: 'var(--text-main)', fontSize: '13px',
                fontFamily: 'inherit', cursor: 'pointer', appearance: 'none' }}>
              <option value="all">Все залы</option>
              {zones.filter(z => z !== 'all').map(z => <option key={z} value={z}>{z}</option>)}
            </select>
            <ChevronDown size={12} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
          </div>

          <button className="btn btn-secondary" onClick={load} disabled={loading} title="Обновить">
            <RefreshCw size={14} />
          </button>
          <button className="btn btn-primary" onClick={() => setModal({ mode: 'create' })}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={14} /> Забронировать
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: 'flex', gap: '10px' }}>
        {[
          { label: 'Активных броней', value: activeBookings.length, color: '#6366f1' },
          { label: 'Сегодня', value: todayBookings.length, color: '#10b981' },
          { label: 'Всего ПК', value: filteredPcs.length, color: 'var(--text-muted)' },
        ].map(s => (
          <div key={s.label} style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
            borderRadius: '10px', padding: '10px 16px', display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span style={{ fontSize: '22px', fontWeight: 700, color: s.color }}>{s.value}</span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{s.label}</span>
          </div>
        ))}
      </div>

      {/* Timeline */}
      {loading ? (
        <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>Загрузка…</div>
      ) : (
        <GanttTimeline
          pcs={filteredPcs}
          bookings={bookings}
          selectedDate={selectedDate}
          onEdit={(b) => setModal({ mode: 'edit', booking: b })}
          onCreateAt={() => setModal({ mode: 'create' })}
        />
      )}

      {/* Modal */}
      {modal && (
        <BookingModal
          mode={modal.mode}
          booking={modal.booking}
          bookings={bookings}
          pcs={pcs}
          clubId={clubId}
          onClose={() => setModal(null)}
          onSaved={load}
        />
      )}
    </div>
  );
};

export default Booking;
