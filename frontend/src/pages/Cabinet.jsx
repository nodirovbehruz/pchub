import { useState, useEffect, useCallback } from 'react';
import {
  Building2, Monitor, Users, Zap, Calendar, Crown, CheckCircle,
  AlertTriangle, RefreshCw, ChevronRight, Clock, Globe, MapPin, Settings, X, Phone,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

const fmtDate = (iso) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' });
};

const daysLeft = (iso) => {
  if (!iso) return null;
  const diff = new Date(iso) - new Date();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
};

// ── Club card ──────────────────────────────────────────────────────────────
const ClubCard = ({ club, stats, onSwitch, isActive }) => {
  const d = club.trial_until ? daysLeft(club.trial_until) : null;
  const isTrial = club.is_trial;
  const isExpiring = d !== null && d <= 7 && d > 0;
  const isExpired = d !== null && d <= 0;

  return (
    <div style={{
      background: 'var(--bg-panel)', borderRadius: '14px',
      border: `1px solid ${isActive ? '#6366f1' : 'var(--border-color)'}`,
      boxShadow: isActive ? '0 0 0 1px rgba(99,102,241,0.3)' : 'none',
      overflow: 'hidden', transition: 'all 0.2s',
    }}>
      {/* Card header */}
      <div style={{ padding: '20px 20px 16px', borderBottom: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ width: 44, height: 44, borderRadius: '12px',
              background: isActive ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.05)',
              display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Building2 size={22} color={isActive ? '#818cf8' : 'var(--text-muted)'} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                {club.name}
                {isActive && (
                  <span style={{ fontSize: '10px', background: '#6366f1', color: '#fff',
                    padding: '2px 8px', borderRadius: '999px', fontWeight: 600 }}>активный</span>
                )}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px',
                display: 'flex', alignItems: 'center', gap: '4px' }}>
                <MapPin size={11} />
                {club.address || club.city || '—'}
              </div>
            </div>
          </div>
          {/* Trial / subscription badge */}
          <div>
            {isTrial && (
              <span style={{
                padding: '4px 12px', borderRadius: '999px', fontSize: '11px', fontWeight: 600,
                background: isExpired ? 'rgba(239,68,68,0.15)' : isExpiring ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.12)',
                color: isExpired ? '#ef4444' : isExpiring ? '#f59e0b' : '#10b981',
                display: 'inline-flex', alignItems: 'center', gap: '4px',
              }}>
                {isExpired ? <AlertTriangle size={11} /> : <Clock size={11} />}
                {isExpired ? 'Trial истёк' : d !== null ? `Trial — ${d}д.` : 'Trial'}
              </span>
            )}
            {!isTrial && (
              <span style={{ padding: '4px 12px', borderRadius: '999px', fontSize: '11px', fontWeight: 600,
                background: 'rgba(99,102,241,0.15)', color: '#818cf8',
                display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <Crown size={11} /> Pro
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', borderBottom: '1px solid var(--border-color)' }}>
        {[
          { icon: Monitor, label: 'ПК',       value: stats?.hosts_state?.total        ?? '—' },
          { icon: Zap,     label: 'Онлайн',  value: stats?.hosts_state?.online       ?? '—' },
          { icon: Users,   label: 'Клиентов',value: stats?.hosts_state?.client_count ?? '—' },
        ].map((item, i) => {
          const Icon = item.icon;
          return (
            <div key={i} style={{ padding: '12px 16px', textAlign: 'center',
              borderRight: i < 2 ? '1px solid var(--border-color)' : 'none' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', marginBottom: '2px' }}>
                <Icon size={13} color="var(--text-muted)" />
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{item.label}</span>
              </div>
              <div style={{ fontSize: '18px', fontWeight: 700 }}>{item.value}</div>
            </div>
          );
        })}
      </div>

      {/* Info + actions */}
      <div style={{ padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', gap: '12px' }}>
          {club.site && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Globe size={11} /> {club.site}
            </span>
          )}
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Calendar size={11} /> с {fmtDate(club.created_at)}
          </span>
          {club.has_shift && (
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#10b981' }}>
              <CheckCircle size={11} /> Смена открыта
            </span>
          )}
        </div>

        {!isActive && (
          <button
            onClick={() => onSwitch(club)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px',
              padding: '7px 14px', borderRadius: '8px', fontSize: '12px', cursor: 'pointer',
              fontFamily: 'inherit', fontWeight: 600,
              background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)',
              color: '#818cf8' }}>
            Перейти <ChevronRight size={14} />
          </button>
        )}
        {isActive && (
          <span style={{ fontSize: '12px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <CheckCircle size={13} /> Активный клуб
          </span>
        )}
      </div>
    </div>
  );
};

// ── Add-club modal ────────────────────────────────────────────────────────────
const AddClubModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({ name: '', city: '', street: '', contact_phone: '' });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { setErr('Введите название клуба'); return; }
    setSaving(true); setErr('');
    try {
      const data = await apiFetch('/api/v1/clubs/my/', {
        method: 'POST',
        body: JSON.stringify({
          name: form.name.trim(),
          city: form.city.trim(),
          street: form.street.trim(),
          contact_phone: form.contact_phone.trim(),
        }),
      });
      onCreated(data);
    } catch (e) {
      setErr(e.message || 'Ошибка создания клуба');
    } finally {
      setSaving(false);
    }
  };

  const inputStyle = {
    width: '100%', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
    borderRadius: 8, padding: '10px 14px', color: 'var(--text-main)',
    fontSize: 14, fontFamily: 'inherit',
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: 440 }}>
        <div className="modal-header">
          <h3 style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Building2 size={18} /> Добавить клуб
          </h3>
          <button className="icon-btn" onClick={onClose}><X size={16} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {err && (
              <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
                color: '#ef4444', padding: '10px 14px', borderRadius: 8, fontSize: 13 }}>
                {err}
              </div>
            )}
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Название клуба <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <input style={inputStyle} placeholder="GameZone, CyberArena…"
                value={form.name} onChange={set('name')} autoFocus required />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Город</label>
                <input style={inputStyle} placeholder="Москва"
                  value={form.city} onChange={set('city')} />
              </div>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                  <Phone size={11} style={{ marginRight: 4 }} />Телефон
                </label>
                <input style={inputStyle} placeholder="+7..." type="tel"
                  value={form.contact_phone} onChange={set('contact_phone')} />
              </div>
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Адрес (улица, дом)</label>
              <input style={inputStyle} placeholder="ул. Ленина, 42"
                value={form.street} onChange={set('street')} />
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '8px 12px',
              background: 'rgba(99,102,241,0.06)', borderRadius: 8, border: '1px solid rgba(99,102,241,0.15)' }}>
              💡 Новый клуб будет создан в режиме Trial. Все настройки доступны в разделе «Настройки» после входа в клуб.
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Отмена</button>
            <button type="submit" className="btn btn-primary" disabled={saving || !form.name.trim()}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              {saving ? '…' : <><Building2 size={14} /> Создать клуб</>}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ── Cabinet page ─────────────────────────────────────────────────────────────
const Cabinet = ({ onClubSwitch, onNavigate }) => {
  const { toast } = useToast();
  const [clubs, setClubs]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [clubStats, setClubStats] = useState({});
  const [showAddClub, setShowAddClub] = useState(false);

  const activeClubId = localStorage.getItem('active_club_id');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // BUGFIX(#2): default DRF pagination caps at 20 — clubs beyond the 20th
      // never rendered. Raise the limit so the whole network is returned.
      const data = await apiFetch('/api/v1/clubs/my/?limit=500');
      const list = data.results || data || [];
      setClubs(list);

      // Load dashboard stats for each club in parallel
      // Per-club stats: override the X-Club-Id header to THIS club (the backend
      // resolves club from the header first, so without this every card showed the
      // active club's numbers and the network totals summed it N times).
      const statsResults = await Promise.allSettled(
        list.map(c => apiFetch(`/api/v1/billing/dashboard/?club=${c.id}`, {
          headers: { 'X-Club-Id': String(c.id) },
        }))
      );
      const statsMap = {};
      list.forEach((c, i) => {
        if (statsResults[i].status === 'fulfilled') {
          statsMap[c.id] = statsResults[i].value;
        }
      });
      setClubStats(statsMap);
    } catch (e) {
      toast('Ошибка загрузки клубов: ' + e.message, { type: 'error' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSwitch = (club) => {
    localStorage.setItem('active_club_id', String(club.id));
    localStorage.setItem('active_club_name', club.name);
    toast(`Переключено на «${club.name}»`, { type: 'success' });
    if (onClubSwitch) onClubSwitch(club);
    // Reload page to ensure all data is fresh
    window.location.reload();
  };

  const totalOnline = Object.values(clubStats).reduce((s, st) => s + (st?.hosts_state?.online || 0), 0);
  const totalPcs    = Object.values(clubStats).reduce((s, st) => s + (st?.hosts_state?.total  || 0), 0);
  const trialCount  = clubs.filter(c => c.is_trial).length;

  return (
    <div style={{ padding: '0 24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ margin: '0 0 4px', fontSize: '22px', fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Crown size={22} color="#f59e0b" /> Личный кабинет владельца
        </h2>
        <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '13px' }}>
          Управление сетью клубов, подписки и настройки платформы
        </p>
      </div>

      {/* Network summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginBottom: '24px' }}>
        {[
          { label: 'Клубов в сети', value: clubs.length, color: '#6366f1', icon: Building2 },
          { label: 'Всего ПК',      value: totalPcs,     color: '#3b82f6', icon: Monitor },
          { label: 'Онлайн сейчас', value: totalOnline,  color: '#10b981', icon: Zap },
          { label: 'Trial клубов',  value: trialCount,   color: '#f59e0b', icon: Clock },
        ].map(item => {
          const Icon = item.icon;
          return (
            <div key={item.label} style={{ background: 'var(--bg-panel)', borderRadius: '12px',
              border: '1px solid var(--border-color)', padding: '16px 18px',
              display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ width: 40, height: 40, borderRadius: '10px',
                background: `${item.color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon size={18} color={item.color} />
              </div>
              <div>
                <div style={{ fontSize: '22px', fontWeight: 700 }}>{item.value}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{item.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Clubs grid */}
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>Мои клубы</h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={load} disabled={loading}>
            <RefreshCw size={14} />
          </button>
          <button className="btn btn-primary"
            onClick={() => setShowAddClub(true)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <Building2 size={14} /> Добавить клуб
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>Загрузка клубов…</div>
      ) : clubs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)',
          background: 'var(--bg-panel)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
          <Building2 size={40} style={{ marginBottom: '12px', opacity: 0.3 }} />
          <div style={{ fontSize: '15px', fontWeight: 600 }}>Клубов пока нет</div>
          <div style={{ fontSize: '13px', marginTop: '4px', marginBottom: '20px' }}>
            Создайте первый клуб, чтобы начать работу
          </div>
          <button className="btn btn-primary" onClick={() => setShowAddClub(true)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <Building2 size={14} /> Добавить первый клуб
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '16px' }}>
          {clubs.map(club => (
            <ClubCard
              key={club.id}
              club={club}
              stats={clubStats[club.id]}
              isActive={String(club.id) === String(activeClubId)}
              onSwitch={handleSwitch}
            />
          ))}
        </div>
      )}

      {/* Add club modal */}
      {showAddClub && (
        <AddClubModal
          onClose={() => setShowAddClub(false)}
          onCreated={(club) => {
            setShowAddClub(false);
            toast(`Клуб «${club.name}» создан!`, { type: 'success' });
            // BUGFIX(#1): the create response lacks server-computed fields
            // (created_at, is_trial, stats), so the freshly-pushed card rendered
            // blank id/date/stats until a manual refresh. Re-fetch the full list
            // (and per-club stats) so the new card is complete immediately.
            load();
          }}
        />
      )}

      {/* Subscription section */}
      <div style={{ marginTop: '32px', padding: '24px', background: 'var(--bg-panel)',
        borderRadius: '14px', border: '1px solid var(--border-color)' }}>
        <h3 style={{ margin: '0 0 16px', fontSize: '15px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Crown size={16} color="#f59e0b" /> Подписка и тарификация
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
          {[
            { label: 'Тариф платформы', value: 'PCHub Business', color: '#6366f1' },
            { label: 'Период оплаты',   value: 'Ежемесячно',      color: 'var(--text-muted)' },
            { label: 'Поддержка',        value: 'Telegram + Email', color: '#10b981' },
          ].map(item => (
            <div key={item.label} style={{ padding: '14px 16px', background: 'rgba(255,255,255,0.03)',
              borderRadius: '10px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                {item.label}
              </div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: item.color }}>{item.value}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: '16px', display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary"
            onClick={() => onNavigate ? onNavigate('subscription') : null}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <Settings size={14} /> Управление подпиской
          </button>
          <button className="btn btn-secondary"
            onClick={() => onNavigate ? onNavigate('subscription') : null}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <Calendar size={14} /> История платежей
          </button>
        </div>
      </div>
    </div>
  );
};

export default Cabinet;
