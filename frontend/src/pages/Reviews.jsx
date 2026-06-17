import { useState, useEffect, useCallback } from 'react';
import { MessageSquare, RefreshCw, Star, Check } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

const Stars = ({ rating }) => (
  <div style={{ display: 'inline-flex', gap: '2px' }}>
    {[1, 2, 3, 4, 5].map(n => (
      <Star key={n} size={14}
        fill={n <= rating ? '#f59e0b' : 'transparent'}
        color={n <= rating ? '#f59e0b' : 'var(--text-muted)'} />
    ))}
  </div>
);

const Reviews = () => {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all | unread

  const clubId = localStorage.getItem('active_club_id');
  const { toast } = useToast();

  const load = useCallback(async () => {
    if (!clubId) return;
    setLoading(true);
    try {
      // limit=500: stats (avg/tips/counts) are computed client-side over this list —
      // the default 20-row cap made them wrong for clubs with more reviews.
      const json = await apiFetch(`/api/v1/sessions/reviews/?club=${clubId}&limit=500`);
      setReviews(json.results || json || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [clubId]);

  useEffect(() => { load(); }, [load]);

  const markRead = async (id) => {
    try {
      await apiFetch(`/api/v1/sessions/reviews/${id}/read/`, { method: 'PATCH' });
      load();
    } catch (e) {
      toast('Ошибка: ' + e.message, { type: 'error' });
    }
  };

  const filtered = filter === 'unread' ? reviews.filter(r => !r.is_read) : reviews;
  const avgRating = reviews.length > 0
    ? (reviews.reduce((s, r) => s + r.rating, 0) / reviews.length).toFixed(1)
    : '—';
  const totalTips = reviews.reduce((s, r) => s + Number(r.tip_amount || 0), 0);

  return (
    <div style={{ padding: '0 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 600, margin: 0, display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
          <MessageSquare size={20} /> Отзывы клиентов
        </h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}
            style={{ background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
              borderRadius: '8px', padding: '8px 12px', color: 'var(--text-light)', fontSize: '13px' }}>
            <option value="all">Все</option>
            <option value="unread">Непрочитанные</option>
          </select>
          <button className="btn btn-secondary" onClick={load}><RefreshCw size={14} /></button>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
        <Stat label="Всего отзывов" value={reviews.length} />
        <Stat label="Средняя оценка" value={avgRating} icon={<Star size={18} fill="#f59e0b" color="#f59e0b" />} />
        <Stat label="Непрочитано" value={reviews.filter(r => !r.is_read).length} accent="#3b82f6" />
        <Stat label="Чаевых, сум" value={totalTips.toFixed(0)} accent="#10b981" />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {loading && <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Загрузка…</div>}
        {!loading && filtered.length === 0 && (
          <div className="glass-panel" style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
            Отзывов пока нет
          </div>
        )}
        {filtered.map(r => (
          <div key={r.id} style={{
            background: 'var(--bg-panel)', borderRadius: '12px',
            border: `1px solid ${r.is_read ? 'var(--border-color)' : 'rgba(59,130,246,0.4)'}`,
            padding: '16px 20px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Stars rating={r.rating} />
                  <span style={{ fontSize: '14px', fontWeight: 600 }}>
                    {r.is_anonymous ? 'Анонимный' : (r.client_username || 'Гость')}
                  </span>
                  {!r.is_read && (
                    <span style={{ background: '#3b82f6', color: 'white', fontSize: '10px', padding: '2px 8px', borderRadius: '10px' }}>NEW</span>
                  )}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  {r.computer_name && `${r.computer_name} · `}
                  {new Date(r.created_at).toLocaleString('ru-RU')}
                </div>
              </div>
              {!r.is_read && (
                <button className="btn btn-secondary" style={{ fontSize: '12px' }}
                        onClick={() => markRead(r.id)}>
                  <Check size={12} /> Прочитано
                </button>
              )}
            </div>
            {r.comment && <div style={{ fontSize: '14px', color: 'var(--text-light)', lineHeight: 1.5, marginTop: '8px' }}>{r.comment}</div>}
            {Number(r.tip_amount) > 0 && (
              <div style={{ marginTop: '10px', display: 'inline-block', padding: '4px 10px',
                background: 'rgba(16,185,129,0.12)', color: '#10b981',
                fontSize: '12px', borderRadius: '999px', fontWeight: 500,
              }}>💰 Чаевые: {r.tip_amount} сум</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const Stat = ({ label, value, icon, accent }) => (
  <div style={{
    flex: 1, padding: '16px 20px',
    background: 'var(--bg-panel)', borderRadius: '12px', border: '1px solid var(--border-color)',
  }}>
    <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>{label}</div>
    <div style={{ fontSize: '24px', fontWeight: 600, color: accent || 'var(--text-light)', display: 'flex', alignItems: 'center', gap: '8px' }}>
      {icon} {value}
    </div>
  </div>
);

export default Reviews;
