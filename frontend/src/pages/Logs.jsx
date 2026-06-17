import { useState, useEffect, useCallback } from 'react';
import { List, Search, RefreshCw, X, ChevronDown } from 'lucide-react';
import { apiFetch } from '../api/client';

/* ── helpers ── */
const fmtDateTime = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
  catch { return '—'; }
};

/* Maps LogAction values from backend → display config */
const ACTION_CONFIGS = {
  // Payments
  'payment.create':    { label: 'Оплата',             color: '#3b82f6', group: 'payment' },
  'payment.refund':    { label: 'Возврат',             color: '#ef4444', group: 'payment' },
  'deposit.topup':     { label: 'Пополнение депозита', color: '#8b5cf6', group: 'payment' },
  'deposit.transfer':  { label: 'Перевод депозита',    color: '#a78bfa', group: 'payment' },
  // Shifts
  'shift.open':        { label: 'Смена открыта',       color: '#10b981', group: 'shift' },
  'shift.close':       { label: 'Смена закрыта',       color: '#6b7280', group: 'shift' },
  // Sessions
  'session.start':     { label: 'Сеанс начат',         color: '#6366f1', group: 'session' },
  'session.end':       { label: 'Сеанс завершён',      color: '#94a3b8', group: 'session' },
  'session.transfer':  { label: 'Пересадка',           color: '#f59e0b', group: 'session' },
  'session.extend':    { label: 'Продление сеанса',    color: '#818cf8', group: 'session' },
  // Cash orders
  'cash.pko':          { label: 'ПКО (внесение)',      color: '#10b981', group: 'cash' },
  'cash.rko':          { label: 'РКО (изъятие)',       color: '#ef4444', group: 'cash' },
  // Power
  'pc.power_on':       { label: 'ПК включён',          color: '#10b981', group: 'power' },
  'pc.power_off':      { label: 'ПК выключен',         color: '#6b7280', group: 'power' },
  'pc.reboot':         { label: 'ПК перезагружен',     color: '#f59e0b', group: 'power' },
  'pc.high_access':    { label: 'Высокий доступ',      color: '#8b5cf6', group: 'power' },
  // Auth
  'auth.login':        { label: 'Вход сотрудника',     color: '#10b981', group: 'auth' },
  'auth.logout':       { label: 'Выход сотрудника',    color: '#6b7280', group: 'auth' },
  // DB changes
  'db.create':         { label: 'Создание записи',     color: '#6366f1', group: 'db' },
  'db.update':         { label: 'Изменение записи',    color: '#f59e0b', group: 'db' },
  'db.delete':         { label: 'Удаление записи',     color: '#ef4444', group: 'db' },
};

const GROUPS = [
  { id: '',        label: 'Все' },
  { id: 'payment', label: '💰 Платежи' },
  { id: 'shift',   label: '🔓 Смены' },
  { id: 'session', label: '🎮 Сеансы' },
  { id: 'cash',    label: '🏦 Касса' },
  { id: 'power',   label: '⚡ Питание' },
  { id: 'auth',    label: '👤 Авторизация' },
  { id: 'db',      label: '📝 Изменения БД' },
];

const getActionCfg = (action) =>
  ACTION_CONFIGS[action] || { label: action || '—', color: 'var(--text-muted)', group: '' };

const Logs = () => {
  const [logs, setLogs]         = useState([]);
  const [loading, setLoading]   = useState(true);
  const [search, setSearch]     = useState('');
  const [groupFilter, setGroupFilter] = useState('');
  const [expanded, setExpanded] = useState(null);
  const [page, setPage]         = useState(1);
  const PAGE_SIZE = 50;

  const clubId = localStorage.getItem('active_club_id');

  const load = useCallback(async () => {
    if (!clubId) { setLoading(false); return; }
    setLoading(true);
    try {
      // NOTE(#4): the backend `q` param only matches OperationLog.object_repr
      // (icontains). Operator name (subject_username) and the action label are
      // NOT searched server-side — that needs a backend change to extend the
      // queryset filter. We DON'T send `q` here so the server returns the full
      // recent window; search is applied client-side below where we CAN also
      // match the operator and the human action label.
      const url = `/api/v1/billing/logs/?club=${clubId}&limit=500`;
      const data = await apiFetch(url).catch(() => []);
      setLogs(data.results || data || []);
      setPage(1);
    } finally {
      setLoading(false);
    }
  }, [clubId]);

  useEffect(() => { load(); }, [load]);

  // Reset paging whenever the search text changes (load() only reruns on club).
  useEffect(() => { setPage(1); }, [search]);

  // Client-side filtering. IMPORTANT LIMITATION(#4): the group filter and search
  // run only over the newest 500 rows the server returned — older matches are not
  // found. True full-history search/filter requires server-side support (extend
  // `q` to cover subject/action, and add group→action filtering on the backend).
  const q = search.trim().toLowerCase();
  const filtered = logs.filter(l => {
    if (groupFilter && getActionCfg(l.action).group !== groupFilter) return false;
    if (!q) return true;
    // Search across object, operator (subject_username) and the action label —
    // the operator match is what the server `q` can't do, so we do it here.
    const hay = [
      l.object_repr, l.object_type, l.subject_username, getActionCfg(l.action).label,
    ].filter(Boolean).join(' ').toLowerCase();
    return hay.includes(q);
  });
  const visible = filtered.slice(0, page * PAGE_SIZE);
  const hasMore = visible.length < filtered.length;

  return (
    <div style={{ padding: '0 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <List size={20} /> Журнал операций
        </h2>
        <button className="btn btn-secondary" onClick={load} disabled={loading}>
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: '320px' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%',
            transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Поиск по объекту, пользователю…"
            style={{ paddingLeft: '32px', height: '34px', width: '100%',
              background: 'var(--bg-input)', border: '1px solid var(--border-input)',
              borderRadius: '8px', color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit' }}
          />
        </div>

        {/* Group filter pills */}
        <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
          {GROUPS.map(g => (
            <button key={g.id}
              onClick={() => { setGroupFilter(g.id === groupFilter ? '' : g.id); setPage(1); }}
              style={{ padding: '4px 11px', borderRadius: '999px', fontSize: '11px', fontWeight: 600,
                cursor: 'pointer', fontFamily: 'inherit', border: 'none',
                background: groupFilter === g.id ? 'var(--accent)' : 'var(--hover-overlay)',
                color: groupFilter === g.id ? '#fff' : 'var(--text-muted)' }}>
              {g.label}
            </button>
          ))}
        </div>

        {(search || groupFilter) && (
          <button className="icon-btn" onClick={() => { setSearch(''); setGroupFilter(''); }}>
            <X size={14} />
          </button>
        )}
      </div>

      {/* Log table */}
      <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
        borderRadius: '12px', overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            Загрузка журнала…
          </div>
        ) : visible.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <List size={32} style={{ opacity: 0.3, marginBottom: '12px' }} />
            <div>Записей не найдено</div>
          </div>
        ) : (
          <>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-dark)' }}>
                  {['Дата/время', 'Действие', 'Объект', 'Оператор', 'Детали'].map(col => (
                    <th key={col} style={{ padding: '10px 14px', textAlign: 'left', fontSize: '10px',
                      color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase',
                      letterSpacing: '0.5px', whiteSpace: 'nowrap' }}>{col}</th>
                  ))}
                </tr>
              </thead>
                {visible.map(log => {
                  const cfg = getActionCfg(log.action);
                  const isOpen = expanded === log.id;
                  return (
                    <tbody key={log.id}>
                      <tr
                        onClick={() => setExpanded(isOpen ? null : log.id)}
                        style={{ borderBottom: '1px solid var(--border-row)', cursor: 'pointer',
                          transition: 'background 0.1s',
                          background: isOpen ? 'var(--hover-overlay)' : 'transparent' }}
                        onMouseEnter={e => { if (!isOpen) e.currentTarget.style.background = 'var(--hover-overlay)'; }}
                        onMouseLeave={e => { if (!isOpen) e.currentTarget.style.background = 'transparent'; }}>
                        <td style={{ padding: '10px 14px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                          {fmtDateTime(log.created_at)}
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={{ padding: '2px 8px', borderRadius: '999px', fontSize: '11px',
                            fontWeight: 600, background: cfg.color + '22', color: cfg.color }}>
                            {cfg.label}
                          </span>
                        </td>
                        <td style={{ padding: '10px 14px', maxWidth: '200px',
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{log.object_type}</span>{' '}
                          <span style={{ fontWeight: 600 }}>{log.object_repr || '—'}</span>
                        </td>
                        <td style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>
                          {log.subject_username || '—'}
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          {log.payload && Object.keys(log.payload).length > 0 ? (
                            <button style={{ background: 'none', border: 'none', cursor: 'pointer',
                              color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '3px',
                              fontSize: '12px', padding: 0, fontFamily: 'inherit' }}>
                              Детали <ChevronDown size={12}
                                style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }} />
                            </button>
                          ) : '—'}
                        </td>
                      </tr>
                      {isOpen && log.payload && (
                        <tr style={{ background: 'var(--bg-dark)', borderBottom: '1px solid var(--border-row)' }}>
                          <td colSpan={5} style={{ padding: '12px 14px' }}>
                            <pre style={{ margin: 0, fontSize: '11px', color: 'var(--text-muted)',
                              fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                              {JSON.stringify(log.payload, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  );
                })}
            </table>

            {hasMore && (
              <div style={{ padding: '12px', textAlign: 'center' }}>
                <button className="btn btn-secondary" onClick={() => setPage(p => p + 1)}
                  style={{ fontSize: '12px' }}>
                  Загрузить ещё ({filtered.length - visible.length})
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Logs;
