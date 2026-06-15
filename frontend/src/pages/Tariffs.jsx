import { useState, useEffect, useCallback } from 'react';
import {
  Plus, Sun, Moon, Percent, CalendarClock, Clock,
  Trash2, Layers, Edit2, X, RefreshCw, Check,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

// ── Constants ──────────────────────────────────────────────────────────────────
const TYPE_META = {
  subscription: { label: 'Абонемент',    color: '#fb923c', bg: 'rgba(251,146,60,0.10)',   icon: Layers },
  package:      { label: 'Пакетный',     color: '#38bdf8', bg: 'rgba(56,189,248,0.10)',  icon: CalendarClock },
  per_minute:   { label: 'Поминутный',   color: '#a855f7', bg: 'rgba(168,85,247,0.10)',  icon: Clock },
  fixed:        { label: 'Фиксированный',color: '#ec4899', bg: 'rgba(236,72,153,0.10)',  icon: Clock },
};

const DAY_NAMES = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

const EMPTY_FORM = {
  name: '',
  tariff_type: 'fixed',
  price: '',
  minutes: 60,
  valid_until_time: '',
  life_days: 0,
  schedule_days: '1234567',
  schedule_start: '',
  schedule_end: '',
  is_night: false,
  apply_discount: true,
  has_schedule: false,
  is_active: true,
};

const inputStyle = {
  width: '100%',
  background: 'var(--bg-dark)',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
  padding: '9px 12px',
  color: 'var(--text-light)',
  fontSize: '13px',
  fontFamily: 'inherit',
};

const formatTime = (t) => (t ? t.slice(0, 5) : '');

// ── Sub-components ─────────────────────────────────────────────────────────────
const Label = ({ children, style }) => (
  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px', ...style }}>
    {children}
  </div>
);

const Field = ({ label, children, hint, style }) => (
  <div style={{ ...style }}>
    <Label>{label}</Label>
    {children}
    {hint && <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>{hint}</div>}
  </div>
);

// ── Create / Edit modal ────────────────────────────────────────────────────────
const TariffModal = ({ editing, onClose, onSaved }) => {
  const { toast } = useToast();
  const clubId = localStorage.getItem('active_club_id');

  const [form, setForm] = useState(() => {
    if (editing && editing.id) {
      return {
        name: editing.name || '',
        tariff_type: editing.tariff_type || 'fixed',
        price: editing.price != null ? String(editing.price) : '',
        minutes: editing.minutes ?? 60,
        valid_until_time: formatTime(editing.valid_until_time),
        life_days: editing.life_days ?? 0,
        schedule_days: editing.schedule_days || '1234567',
        schedule_start: formatTime(editing.schedule_start),
        schedule_end: formatTime(editing.schedule_end),
        is_night: !!editing.is_night,
        apply_discount: editing.apply_discount !== false,
        has_schedule: !!editing.has_schedule,
        is_active: editing.is_active !== false,
      };
    }
    return { ...EMPTY_FORM };
  });

  const [saving, setSaving] = useState(false);

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }));

  // toggle a day char in schedule_days string
  const toggleDay = (dayNum) => {
    const char = String(dayNum);
    const days = form.schedule_days || '';
    const has = days.includes(char);
    const updated = has
      ? days.replace(char, '')
      : (days + char).split('').sort().join('');
    set('schedule_days', updated);
  };

  const save = async () => {
    if (!form.name.trim()) { toast('Укажите название тарифа', { type: 'warning' }); return; }
    setSaving(true);
    try {
      const body = {
        name: form.name.trim(),
        tariff_type: form.tariff_type,
        price: parseFloat(form.price) || 0,
        minutes: parseInt(form.minutes) || 60,
        life_days: parseInt(form.life_days) || 0,
        schedule_days: form.schedule_days || '1234567',
        is_night: form.is_night,
        apply_discount: form.apply_discount,
        has_schedule: form.has_schedule,
        is_active: form.is_active,
        club: clubId ? Number(clubId) : null,
      };
      if (form.valid_until_time) body.valid_until_time = form.valid_until_time;
      if (form.schedule_start) body.schedule_start = form.schedule_start;
      if (form.schedule_end)   body.schedule_end   = form.schedule_end;

      if (editing?.id) {
        await apiFetch(`/api/v1/billing/tariffs/${editing.id}/`, {
          method: 'PATCH',
          body: JSON.stringify(body),
        });
        toast('Тариф обновлён', { type: 'success' });
      } else {
        await apiFetch('/api/v1/billing/tariffs/', {
          method: 'POST',
          body: JSON.stringify(body),
        });
        toast('Тариф создан', { type: 'success' });
      }
      onSaved();
      onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка сохранения', { type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: 'var(--bg-panel)', borderRadius: '16px', padding: '24px',
        width: '560px', maxWidth: '95vw', maxHeight: '90vh', overflow: 'auto',
        border: '1px solid var(--border-color)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ margin: 0, fontSize: '16px' }}>
            {editing?.id ? 'Редактирование тарифа' : 'Новый тариф'}
          </h3>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>

        {/* Section 1 — Basic */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
          <Field label="Тип тарифа" style={{ gridColumn: '1 / -1' }}>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {Object.entries(TYPE_META).map(([key, meta]) => {
                const Icon = meta.icon;
                const sel = form.tariff_type === key;
                return (
                  <button key={key} type="button" onClick={() => set('tariff_type', key)}
                    style={{
                      padding: '6px 14px', borderRadius: '8px', cursor: 'pointer',
                      fontFamily: 'inherit', fontSize: '12px', fontWeight: 500,
                      display: 'inline-flex', alignItems: 'center', gap: '5px',
                      background: sel ? meta.bg : 'rgba(255,255,255,0.03)',
                      border: `1px solid ${sel ? meta.color : 'var(--border-color)'}`,
                      color: sel ? meta.color : 'var(--text-muted)',
                      transition: 'all 0.15s',
                    }}>
                    <Icon size={13} /> {meta.label}
                  </button>
                );
              })}
            </div>
          </Field>

          <Field label="Название *" style={{ gridColumn: '1 / -1' }}>
            <input type="text" value={form.name}
              onChange={(e) => set('name', e.target.value)}
              placeholder="Например: Ночной пакет"
              style={inputStyle} autoFocus />
          </Field>

          <Field label="Базовая цена (сум)">
            <input type="number" value={form.price} min="0" step="0.01"
              onChange={(e) => set('price', e.target.value)}
              placeholder="0" style={inputStyle} />
          </Field>

          {form.tariff_type !== 'package' && form.tariff_type !== 'per_minute' && (
            <Field label="Минуты">
              <input type="number" value={form.minutes} min="1"
                onChange={(e) => set('minutes', e.target.value)}
                placeholder="60" style={inputStyle} />
            </Field>
          )}

          {form.tariff_type === 'package' && (
            <Field label="Действует до (время)" hint="Пакет действует до этого времени суток">
              <input type="time" value={form.valid_until_time}
                onChange={(e) => set('valid_until_time', e.target.value)}
                style={inputStyle} />
            </Field>
          )}

          {form.tariff_type === 'subscription' && (
            <Field label="Срок действия (дней)" hint="Купленные часы действуют N дней">
              <input type="number" value={form.life_days} min="0"
                onChange={(e) => set('life_days', e.target.value)}
                placeholder="30" style={inputStyle} />
            </Field>
          )}
        </div>

        {/* Section 2 — Schedule */}
        <div style={{
          background: 'var(--bg-dark)', borderRadius: '10px',
          padding: '14px 16px', marginBottom: '14px',
          border: '1px solid var(--border-color)',
        }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', fontWeight: 500, marginBottom: '12px' }}>
            <input type="checkbox" checked={form.has_schedule}
              onChange={(e) => set('has_schedule', e.target.checked)} />
            Ограничить по расписанию
          </label>

          {form.has_schedule && (
            <>
              {/* Days of week */}
              <div style={{ marginBottom: '12px' }}>
                <Label>Дни недели</Label>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {DAY_NAMES.map((name, i) => {
                    const dayNum = i + 1;
                    const active = (form.schedule_days || '').includes(String(dayNum));
                    return (
                      <button key={dayNum} type="button" onClick={() => toggleDay(dayNum)}
                        style={{
                          width: '36px', height: '36px', borderRadius: '8px', cursor: 'pointer',
                          fontFamily: 'inherit', fontSize: '12px', fontWeight: 600,
                          background: active ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.03)',
                          border: `1px solid ${active ? '#6366f1' : 'var(--border-color)'}`,
                          color: active ? '#a5b4fc' : 'var(--text-muted)',
                          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        }}>
                        {name}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Time range */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <Field label="Время начала">
                  <input type="time" value={form.schedule_start}
                    onChange={(e) => set('schedule_start', e.target.value)}
                    style={inputStyle} />
                </Field>
                <Field label="Время окончания">
                  <input type="time" value={form.schedule_end}
                    onChange={(e) => set('schedule_end', e.target.value)}
                    style={inputStyle} />
                </Field>
              </div>
            </>
          )}
        </div>

        {/* Section 3 — Flags */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '24px' }}>
          {[
            { key: 'is_night',        label: 'Ночной тариф',                  icon: Moon,    color: '#818cf8' },
            { key: 'apply_discount',  label: 'Применять скидки клуба',         icon: Percent, color: '#10b981' },
            { key: 'is_active',       label: 'Тариф активен (виден клиентам)', icon: Check,   color: '#10b981' },
          ].map(({ key, label, icon: Icon, color }) => (
            <label key={key} style={{ display: 'flex', alignItems: 'center', gap: '10px',
              cursor: 'pointer', fontSize: '13px' }}>
              <input type="checkbox" checked={!!form[key]}
                onChange={(e) => set(key, e.target.checked)} />
              <Icon size={14} color={form[key] ? color : 'var(--text-muted)'} />
              <span style={{ color: form[key] ? 'var(--text-light)' : 'var(--text-muted)' }}>{label}</span>
            </label>
          ))}
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Отмена</button>
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? 'Сохранение…' : (editing?.id ? 'Сохранить' : 'Создать тариф')}
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Main page ──────────────────────────────────────────────────────────────────
const Tariffs = () => {
  const { toast } = useToast();
  const [tariffs, setTariffs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // null | {} (create) | {id, ...} (edit)

  const clubId = localStorage.getItem('active_club_id');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = clubId
        ? `/api/v1/billing/tariffs/?club=${clubId}`
        : `/api/v1/billing/tariffs/`;
      const json = await apiFetch(url);
      setTariffs(json.results || json || []);
    } catch (e) {
      console.error(e);
      toast('Ошибка загрузки тарифов', { type: 'error' });
    } finally {
      setLoading(false);
    }
  }, [clubId]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (t) => {
    if (!window.confirm(`Удалить тариф «${t.name}»?`)) return;
    try {
      await apiFetch(`/api/v1/billing/tariffs/${t.id}/`, { method: 'DELETE' });
      toast('Тариф удалён', { type: 'success' });
      load();
    } catch (e) {
      toast('Ошибка удаления: ' + e.message, { type: 'error' });
    }
  };

  const groupPrices = (tariff) => {
    const map = new Map();
    for (const p of tariff.prices || []) {
      if (!map.has(p.group)) map.set(p.group, { name: p.group_name, day: null, night: null });
      map.get(p.group)[p.period] = p.price;
    }
    return Array.from(map.values());
  };

  return (
    <div style={{ padding: '0 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 600, margin: 0 }}>Тарифы</h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={load} title="Обновить"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <RefreshCw size={14} />
          </button>
          <button className="btn btn-primary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            onClick={() => setModal({})}>
            <Plus size={14} /> Добавить тариф
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px' }}>Загрузка…</div>
      )}

      {/* Empty state */}
      {!loading && tariffs.length === 0 && (
        <div className="glass-panel" style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          <Layers size={40} style={{ opacity: 0.3, display: 'block', margin: '0 auto 12px' }} />
          Тарифов ещё нет. Нажмите «Добавить тариф» чтобы создать первый.
        </div>
      )}

      {/* Card grid */}
      {!loading && tariffs.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '16px',
        }}>
          {tariffs.map(t => {
            const meta = TYPE_META[t.tariff_type] || TYPE_META.fixed;
            const MetaIcon = meta.icon;
            const prices = groupPrices(t);
            return (
              <div key={t.id} style={{
                background: 'var(--bg-panel)',
                border: '1px solid var(--border-color)',
                borderRadius: '14px',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }}>
                {/* Coloured header strip */}
                <div style={{
                  padding: '10px 16px',
                  background: meta.bg,
                  borderBottom: `1px solid ${meta.color}33`,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px',
                    fontSize: '12px', fontWeight: 600, color: meta.color }}>
                    <MetaIcon size={14} />
                    {meta.label}
                  </span>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <button onClick={() => setModal(t)}
                      style={{ background: 'transparent', border: 'none', color: meta.color,
                        cursor: 'pointer', display: 'flex', padding: '2px 4px' }}
                      title="Редактировать">
                      <Edit2 size={13} />
                    </button>
                    <button onClick={() => handleDelete(t)}
                      style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)',
                        cursor: 'pointer', display: 'flex', padding: '2px 4px' }}
                      title="Удалить">
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>

                <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
                  <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-light)' }}>
                    {t.name}
                  </div>

                  {/* Feature icons */}
                  <div style={{ display: 'flex', gap: '8px', color: 'var(--text-muted)' }}>
                    {t.is_night && <Moon size={14} title="Ночной тариф" color="#818cf8" />}
                    {t.apply_discount && <Percent size={14} title="Применяются скидки" color="#10b981" />}
                    {t.has_schedule && <CalendarClock size={14} title="С расписанием" color="#f59e0b" />}
                    {!t.is_active && (
                      <span style={{ fontSize: '11px', background: 'rgba(239,68,68,0.1)', color: '#ef4444',
                        padding: '2px 8px', borderRadius: '999px' }}>неактивен</span>
                    )}
                  </div>

                  {/* Prices */}
                  {prices.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {prices.map((p, idx) => (
                        <div key={idx} style={{
                          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px',
                          paddingTop: '10px',
                          borderTop: idx === 0 ? `1px dashed ${meta.color}44` : '1px solid var(--border-color)',
                        }}>
                          <div>
                            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Зал</div>
                            <div style={{ fontSize: '13px', color: 'var(--text-light)', marginTop: '2px' }}>{p.name}</div>
                          </div>
                          <div>
                            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Цена</div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '2px' }}>
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '13px', color: 'var(--text-light)' }}>
                                <Sun size={11} color="#fbbf24" /> {p.day != null ? `${parseFloat(p.day)} сум` : '—'}
                              </span>
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '12px', color: 'var(--text-muted)' }}>
                                <Moon size={11} /> {p.night != null ? `${parseFloat(p.night)} сум` : '—'}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Базовая цена: <span style={{ color: meta.color, fontWeight: 600 }}>{t.price} сум</span>
                    </div>
                  )}

                  {/* Duration + schedule */}
                  <div style={{
                    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px',
                    paddingTop: '10px', borderTop: '1px solid var(--border-color)',
                    marginTop: 'auto',
                  }}>
                    <div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Длительность</div>
                      <div style={{ fontSize: '13px', color: 'var(--text-light)', marginTop: '2px' }}>{t.hours_display}</div>
                      {t.tariff_type === 'subscription' && t.life_days > 0 && (
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          Срок: {t.life_days} д.
                        </div>
                      )}
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: meta.color, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        {t.tariff_type === 'fixed' ? 'График продажи' : 'График действия'}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-light)', marginTop: '2px', lineHeight: 1.4 }}>
                        {t.days_label || '—'}
                      </div>
                      {(t.schedule_start || t.schedule_end) && (
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {formatTime(t.schedule_start) || '00:00'} — {formatTime(t.schedule_end) || '00:00'}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal */}
      {modal !== null && (
        <TariffModal
          editing={modal}
          onClose={() => setModal(null)}
          onSaved={load}
        />
      )}
    </div>
  );
};

export default Tariffs;
