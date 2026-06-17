import { useState, useEffect, useCallback } from 'react';
import { Bell, Monitor, User, Clock, CheckCircle, RefreshCw, Phone } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

const fmtTime = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

const fmtDate = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }) + ' ' + fmtTime(iso);
};

const AdminCalls = ({ onCountChange }) => {
  const { toast } = useToast();
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [answering, setAnswering] = useState(null);
  const [filter, setFilter] = useState('unanswered'); // 'all' | 'unanswered' | 'answered'

  const clubId = localStorage.getItem('active_club_id');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // limit=500: list + unanswered badge were capped at 20 by default pagination.
      const json = await apiFetch(`/api/v1/sessions/admin-calls/?limit=500${clubId ? `&club=${clubId}` : ''}`);
      const list = json.results || json || [];
      setCalls(list);
      // Notify parent about unanswered count
      const unanswered = list.filter(c => !c.is_answered).length;
      if (onCountChange) onCountChange(unanswered);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [clubId, onCountChange]);

  useEffect(() => { load(); }, [load]);

  const handleAnswer = async (call) => {
    setAnswering(call.id);
    try {
      await apiFetch(`/api/v1/sessions/admin-calls/${call.id}/answer/`, { method: 'PATCH', body: '{}' });
      toast('Вызов отмечен как отвеченный', { type: 'success' });
      load();
    } catch (e) {
      toast('Ошибка: ' + e.message, { type: 'error' });
    } finally {
      setAnswering(null);
    }
  };

  const filtered = calls.filter(c => {
    if (filter === 'unanswered') return !c.is_answered;
    if (filter === 'answered') return c.is_answered;
    return true;
  });

  const unansweredCount = calls.filter(c => !c.is_answered).length;

  return (
    <div style={{ padding: '0 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Bell size={20} />
            Вызовы оператора
            {unansweredCount > 0 && (
              <span style={{ background: '#ef4444', color: '#fff', borderRadius: '999px',
                padding: '2px 10px', fontSize: '13px', fontWeight: 700 }}>
                {unansweredCount}
              </span>
            )}
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
            Запросы клиентов «Позвать администратора» из SmartShell
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {/* Filter tabs */}
          {[
            { v: 'unanswered', l: 'Новые' },
            { v: 'answered',   l: 'Отвеченные' },
            { v: 'all',        l: 'Все' },
          ].map(f => (
            <button key={f.v} onClick={() => setFilter(f.v)}
              style={{ padding: '6px 14px', borderRadius: '8px', fontSize: '12px', cursor: 'pointer',
                fontFamily: 'inherit',
                background: filter === f.v ? 'rgba(99,102,241,0.2)' : 'var(--bg-dark)',
                border: `1px solid ${filter === f.v ? '#6366f1' : 'var(--border-color)'}`,
                color: filter === f.v ? '#a5b4fc' : 'var(--text-muted)' }}>
              {f.l}
            </button>
          ))}
          <button className="btn btn-secondary" onClick={load} title="Обновить">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Calls list */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>Загрузка…</div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)',
          background: 'var(--bg-panel)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
          {filter === 'unanswered' ? (
            <>
              <CheckCircle size={40} color="#10b981" style={{ marginBottom: '12px', opacity: 0.5 }} />
              <div style={{ fontSize: '15px', fontWeight: 600 }}>Новых вызовов нет</div>
              <div style={{ fontSize: '13px', marginTop: '4px' }}>Все клиенты обслужены 👍</div>
            </>
          ) : (
            <div style={{ fontSize: '14px' }}>Вызовов не найдено</div>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {filtered.map(call => (
            <div key={call.id}
              style={{ background: 'var(--bg-panel)', border: `1px solid ${!call.is_answered ? 'rgba(239,68,68,0.3)' : 'var(--border-color)'}`,
                borderRadius: '12px', padding: '16px 20px',
                display: 'flex', alignItems: 'center', gap: '16px',
                boxShadow: !call.is_answered ? '0 0 0 1px rgba(239,68,68,0.1)' : 'none',
                transition: 'all 0.2s' }}>

              {/* Status dot */}
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', flexShrink: 0,
                background: call.is_answered ? '#10b981' : '#ef4444',
                boxShadow: !call.is_answered ? '0 0 0 4px rgba(239,68,68,0.2)' : 'none' }} />

              {/* Main info */}
              <div style={{ flex: 1, display: 'flex', gap: '24px', flexWrap: 'wrap', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '120px' }}>
                  <Monitor size={15} color="var(--text-muted)" />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>
                      {call.computer_name || (call.computer ? `ПК #${call.computer}` : 'Неизвестный ПК')}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: '120px' }}>
                  <User size={15} color="var(--text-muted)" />
                  <div style={{ fontSize: '13px', color: 'var(--text-light)' }}>
                    {call.client_username || call.client || 'Гость'}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Clock size={15} color="var(--text-muted)" />
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {fmtDate(call.called_at)}
                  </div>
                </div>

                {call.is_answered && call.answered_at && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#10b981' }}>
                    <CheckCircle size={13} />
                    Отвечено в {fmtTime(call.answered_at)}
                  </div>
                )}

                {call.note && (
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic',
                    padding: '4px 10px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px' }}>
                    «{call.note}»
                  </div>
                )}
              </div>

              {/* Action */}
              {!call.is_answered && (
                <button
                  onClick={() => handleAnswer(call)}
                  disabled={answering === call.id}
                  style={{ padding: '8px 18px', borderRadius: '8px', border: 'none',
                    background: '#10b981', color: '#fff', cursor: 'pointer',
                    fontSize: '13px', fontWeight: 600, fontFamily: 'inherit',
                    display: 'flex', alignItems: 'center', gap: '6px',
                    opacity: answering === call.id ? 0.6 : 1,
                    flexShrink: 0 }}>
                  <Phone size={13} />
                  {answering === call.id ? 'Отмечаю…' : 'Ответил'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AdminCalls;
