import { useState, useEffect, useCallback } from 'react';
import {
  Monitor, Zap, Users, Wrench, ShieldX, Key,
  RefreshCw, CheckSquare, Square, ShoppingCart, Package,
  Clock, Wallet, TrendingUp, Star,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

const fmtMoney = (v) => Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 1 }) + ' сум';
const fmtTime  = (iso) => { try { return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }); } catch { return '—'; } };
const fmtDate  = (iso) => { try { return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }); } catch { return '—'; } };

// ── Top financial card ────────────────────────────────────────────────────────
const FinCard = ({ label, value, sub, subColor, icon: Icon, iconBg, pct }) => (
  <div style={{
    background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
    borderRadius: '12px', padding: '14px 16px', minWidth: '140px', flexShrink: 0,
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
      {Icon && (
        <span style={{ width: 22, height: 22, borderRadius: '6px', background: iconBg || 'rgba(99,102,241,0.15)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <Icon size={12} color={subColor || '#6366f1'} />
        </span>
      )}
      <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500 }}>{label}</span>
    </div>
    <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-light)', lineHeight: 1.1 }}>{value}</div>
    {(sub || pct != null) && (
      <div style={{ marginTop: '4px', fontSize: '11px', color: subColor || '#10b981', fontWeight: 500 }}>
        {pct != null ? `${pct}%` : sub}
      </div>
    )}
  </div>
);

// ── Shift summary card (wider) ────────────────────────────────────────────────
const ShiftCard = ({ shift }) => (
  <div style={{
    background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
    borderRadius: '12px', padding: '14px 18px', minWidth: '200px', flexShrink: 0,
    borderLeft: '3px solid #10b981',
  }}>
    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 500 }}>
      Выручка
    </div>
    <div style={{ fontSize: '22px', fontWeight: 800, color: '#10b981', lineHeight: 1 }}>
      {fmtMoney(shift?.expected_cash || 0)}
    </div>
    <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
        Наличных в кассе: <span style={{ color: 'var(--text-light)', fontWeight: 600 }}>
          {fmtMoney(shift?.cash_revenue || 0)}</span>
      </div>
      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
        На начало смены: <span style={{ color: 'var(--text-light)', fontWeight: 600 }}>
          {fmtMoney(shift?.initial_cash || 0)}</span>
      </div>
    </div>
  </div>
);

// ── PC status bar ─────────────────────────────────────────────────────────────
const PcBar = ({ h }) => {
  const items = [
    { icon: Monitor, label: 'Компьютеры',   value: h.total,          color: 'var(--text-muted)' },
    { icon: Zap,     label: 'Включены',     value: h.online,         color: '#10b981' },
    { icon: Users,   label: 'Активный сеанс', value: h.active_sessions, color: '#6366f1' },
    { icon: Users,   label: 'Анонимных',    value: 0,                color: 'var(--text-muted)' },
    { icon: Wrench,  label: 'Обслуживание', value: h.maintenance,    color: '#f59e0b' },
    { icon: Key,     label: 'Высокий доступ', value: h.high_access || 0, color: '#a855f7' },
    // «Шелл отключен» убрано — не было реального источника статуса (всегда 0).
  ];
  return (
    <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
      borderRadius: '12px', padding: '0 4px', display: 'flex', alignItems: 'stretch',
      overflow: 'hidden' }}>
      {items.map((item, i) => {
        const Icon = item.icon;
        return (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '10px 16px', flex: 1, minWidth: 0,
            borderRight: i < items.length - 1 ? '1px solid var(--border-color)' : 'none',
          }}>
            <Icon size={14} color={item.color} style={{ flexShrink: 0 }} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', whiteSpace: 'nowrap',
                overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.label}</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: item.color }}>{item.value ?? '—'}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ── Panel with tabs ─────────────────────────────────────────────────────────
const TabPanel = ({ tabs, activeTab, setActiveTab, children, style }) => (
  <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
    borderRadius: '12px', display: 'flex', flexDirection: 'column', overflow: 'hidden', ...style }}>
    <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)',
      background: 'var(--bg-dark)' }}>
      {tabs.map(tab => (
        <button key={tab.id} onClick={() => setActiveTab(tab.id)}
          style={{ padding: '10px 16px', background: 'none', border: 'none',
            cursor: 'pointer', fontFamily: 'inherit', fontSize: '12px', fontWeight: 500,
            borderBottom: `2px solid ${activeTab === tab.id ? 'var(--accent)' : 'transparent'}`,
            color: activeTab === tab.id ? 'var(--text-light)' : 'var(--text-muted)',
            transition: 'all 0.15s', whiteSpace: 'nowrap' }}>
          {tab.label}
          {tab.count != null && tab.count > 0 && (
            <span style={{ marginLeft: '6px', background: 'rgba(99,102,241,0.2)', color: '#818cf8',
              borderRadius: '999px', padding: '1px 6px', fontSize: '10px' }}>{tab.count}</span>
          )}
        </button>
      ))}
    </div>
    <div style={{ flex: 1, overflow: 'auto' }}>{children}</div>
  </div>
);

// ── Dashboard ─────────────────────────────────────────────────────────────────
const Dashboard = () => {
  const { toast } = useToast();
  const [data, setData]           = useState(null);
  const [clients, setClients]     = useState([]);
  const [loading, setLoading]     = useState(true);
  const [taskTab, setTaskTab]     = useState('active');
  const [saleTab, setSaleTab]     = useState('tariffs');
  const [clientPeriod, setClientPeriod] = useState('day');
  const [accountTab, setAccountTab] = useState('occupied');
  const [newTask, setNewTask]     = useState('');
  const [addingTask, setAddingTask] = useState(false);

  const clubId = localStorage.getItem('active_club_id');

  const load = useCallback(async () => {
    if (!clubId) { setLoading(false); return; }
    try {
      const [dashJson, clientJson] = await Promise.all([
        apiFetch(`/api/v1/billing/dashboard/?club=${clubId}`).catch(() => null),
        apiFetch(`/api/v1/billing/admin/users/?club=${clubId}`).catch(() => ({ results: [] })),
      ]);
      setData(dashJson);
      setClients(clientJson?.results || clientJson || []);
    } catch (e) {
      console.error('Dashboard fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [clubId]);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  const toggleTask = async (taskId) => {
    try {
      await apiFetch(`/api/v1/content/tasks/${taskId}/`, {
        method: 'PATCH',
        body: JSON.stringify({ is_finished: true }),
      });
      toast('Задача выполнена', { type: 'success' });
      load();
    } catch { /* ignore */ }
  };

  const createTask = async () => {
    const title = newTask.trim();
    // Always give feedback so the button never feels "dead": empty field / no club were
    // silent returns before (looked like the button didn't work). Log the click so the
    // console shows whether it even fired and with what title/club.
    console.log('[createTask] click — title:', JSON.stringify(title), '| club:', clubId);
    if (!title) { toast('Сначала введите текст задачи', { type: 'warning' }); return; }
    if (!clubId) { toast('Клуб не выбран — перезайдите в аккаунт', { type: 'error' }); return; }
    setAddingTask(true);
    try {
      await apiFetch('/api/v1/content/tasks/', {
        method: 'POST',
        body: JSON.stringify({ club: Number(clubId), title }),
      });
      toast('Задача создана', { type: 'success' });
      setNewTask('');
      load();
    } catch (e) {
      // Surface the backend's reason (e.g. «Нет доступа к клубу») instead of a bare
      // "HTTP 4xx", and log the full detail so the cause is visible in the console.
      console.error('createTask failed:', e?.status, e?.body || e);
      toast('Ошибка: ' + (e?.body?.error || e?.body?.detail || e?.message || 'server error'), { type: 'error' });
    } finally {
      setAddingTask(false);
    }
  };

  if (loading) return (
    <div style={{ padding: '40px', color: 'var(--text-muted)', textAlign: 'center' }}>Загрузка дашборда…</div>
  );
  if (!clubId) return (
    <div style={{ padding: '40px', color: 'var(--text-muted)', textAlign: 'center' }}>
      <div style={{ fontSize: '16px', marginBottom: '8px' }}>Клуб не выбран</div>
      <div style={{ fontSize: '12px' }}>Войдите и выберите активный клуб</div>
    </div>
  );
  if (!data) return (
    <div style={{ padding: '40px', color: 'var(--text-muted)', textAlign: 'center' }}>
      <div style={{ fontSize: '16px', marginBottom: '8px' }}>Нет связи с сервером</div>
      <div style={{ fontSize: '12px' }}>Убедитесь что backend запущен на :8000</div>
      <button className="btn btn-primary" style={{ marginTop: '16px' }} onClick={load}>Повторить</button>
    </div>
  );

  const s  = data.shift_info || {};
  const r  = data.revenue_by_category || {};
  const h  = data.hosts_state || {};
  const ba = data.bonus_activity || {};
  const totalCash = Number(s.cash_revenue || 0);
  const totalCard = Number(s.card_revenue || 0);
  const totalRev  = totalCash + totalCard;
  const cashPct   = totalRev > 0 ? ((totalCash / totalRev) * 100).toFixed(2) : '0.00';
  const cardPct   = totalRev > 0 ? ((totalCard / totalRev) * 100).toFixed(2) : '0.00';

  // Shift items
  const tariffsSold = data.shift_items?.products_sold?.filter(i => i.type === 'tariff') || data.shift_items?.products_sold || [];
  const productsSold = data.shift_items?.products_sold?.filter(i => i.type !== 'tariff') || [];
  const servicesSold = data.shift_items?.services_provided || [];

  // Active clients (online first) — backend returns is_active
  const activeClients = clients
    .filter(c => c.is_active || c.is_active_session || c.has_active_session)
    .slice(0, 20);

  const occupiedAccounts = (data.account_groups || []).filter(a => a.in_use);
  const allAccounts      = data.account_groups || [];

  return (
    <div style={{ padding: '0 24px 24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>

      {/* ── Top header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>Дашборд</h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {s.opened_at && (
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Смена с {fmtTime(s.opened_at)} · {s.operator || ''}
            </span>
          )}
          <button className="btn btn-secondary" onClick={load} style={{ padding: '6px 10px' }}>
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* ── Financial strip ── */}
      <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '4px' }}>
        <ShiftCard shift={s} />
        <FinCard label="Наличные" value={fmtMoney(s.cash_revenue)}
          sub={`${cashPct}%`} subColor="#10b981"
          icon={Wallet} iconBg="rgba(16,185,129,0.12)" />
        <FinCard label="Карта" value={fmtMoney(s.card_revenue)}
          sub={`${cardPct}%`} subColor="#3b82f6"
          icon={TrendingUp} iconBg="rgba(59,130,246,0.12)" />
        <FinCard label="Тарифы" value={fmtMoney(r.tariffs)}
          icon={Clock} iconBg="rgba(251,146,60,0.12)" subColor="#fb923c" />
        <FinCard label="Товары" value={fmtMoney(r.products)}
          icon={Package} iconBg="rgba(56,189,248,0.12)" subColor="#38bdf8" />
        <FinCard label="Пополнения" value={fmtMoney(r.topups)}
          icon={Wallet} iconBg="rgba(168,85,247,0.12)" subColor="#a855f7" />
        <FinCard label="Услуги" value={fmtMoney(r.services)}
          icon={Star} iconBg="rgba(236,72,153,0.12)" subColor="#ec4899" />
        <FinCard label="Траты с депозита" value={fmtMoney(ba.deposit_spent_total)}
          icon={ShoppingCart} iconBg="rgba(245,158,11,0.12)" subColor="#f59e0b" />
        <FinCard label="Бонусные пополнения" value={fmtMoney(ba.bonus_topups_total)}
          icon={Star} iconBg="rgba(16,185,129,0.12)" subColor="#10b981" />
      </div>

      {/* ── PC status bar ── */}
      <PcBar h={h} />

      {/* ── Tasks + Shift items ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>

        {/* Tasks panel */}
        <TabPanel
          tabs={[
            { id: 'active',   label: 'Активные задачи',    count: (data.tasks?.active || []).length },
            { id: 'finished', label: 'Завершенные задачи', count: (data.tasks?.finished || []).length },
          ]}
          activeTab={taskTab} setActiveTab={setTaskTab}
          style={{ minHeight: '220px' }}>
          {taskTab === 'active' && (
            <div style={{ padding: '0' }}>
              {/* Quick create task */}
              <div style={{ display: 'flex', gap: '6px', padding: '10px 12px',
                borderBottom: '1px solid var(--border-color)' }}>
                <input
                  value={newTask}
                  onChange={e => setNewTask(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && createTask()}
                  placeholder="Новая задача…"
                  style={{ flex: 1, height: '32px', padding: '0 10px', background: 'var(--bg-dark)',
                    border: '1px solid var(--border-color)', borderRadius: '6px',
                    color: 'var(--text-light)', fontSize: '12px', fontFamily: 'inherit' }}
                />
                <button className="btn btn-primary" onClick={createTask} disabled={addingTask}
                  style={{ padding: '0 12px', fontSize: '12px', height: '32px' }}>
                  {addingTask ? '…' : '+ Добавить'}
                </button>
              </div>
              {(data.tasks?.active || []).length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                  Нет активных задач
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <th style={{ padding: '8px 16px', textAlign: 'left', fontSize: '10px',
                        color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        Задача
                      </th>
                      <th style={{ padding: '8px 16px', textAlign: 'left', fontSize: '10px',
                        color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px', width: '110px' }}>
                        Срок
                      </th>
                      <th style={{ padding: '8px 16px', textAlign: 'left', fontSize: '10px',
                        color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px', width: '90px' }}>
                        Исполнитель
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.tasks?.active || []).map(t => (
                      <tr key={t.id} style={{ borderBottom: '1px solid var(--border-row)' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <td style={{ padding: '9px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <button onClick={() => toggleTask(t.id)}
                              style={{ background: 'none', border: 'none', cursor: 'pointer',
                                color: 'var(--text-muted)', padding: 0, display: 'flex' }}>
                              <Square size={14} />
                            </button>
                            <span style={{ color: 'var(--text-light)' }}>{t.title}</span>
                          </div>
                        </td>
                        <td style={{ padding: '9px 16px', color: 'var(--text-muted)' }}>
                          {t.deadline ? fmtDate(t.deadline) : '—'}
                        </td>
                        <td style={{ padding: '9px 16px', color: 'var(--text-muted)' }}>—</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
          {taskTab === 'finished' && (
            <div>
              {(data.tasks?.finished || []).length === 0 ? (
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                  Нет завершённых задач
                </div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                  <tbody>
                    {(data.tasks?.finished || []).map(t => (
                      <tr key={t.id} style={{ borderBottom: '1px solid var(--border-row)' }}>
                        <td style={{ padding: '9px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <CheckSquare size={14} color="#10b981" />
                            <span style={{ color: 'var(--text-muted)', textDecoration: 'line-through' }}>{t.title}</span>
                          </div>
                        </td>
                        <td style={{ padding: '9px 16px', color: 'var(--text-muted)', fontSize: '12px' }}>
                          {t.finished_at ? fmtDate(t.finished_at) : ''}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </TabPanel>

        {/* Shift sales panel */}
        <TabPanel
          tabs={[
            { id: 'tariffs',  label: 'Проданные тарифы' },
            { id: 'products', label: 'Проданные товары' },
            { id: 'services', label: 'Оказанные услуги' },
          ]}
          activeTab={saleTab} setActiveTab={setSaleTab}
          style={{ minHeight: '220px' }}>
          {(() => {
            const rows = saleTab === 'tariffs' ? tariffsSold : saleTab === 'products' ? productsSold : servicesSold;
            if (rows.length === 0) return (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                Пока нет данных
              </div>
            );
            return (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    {['Название', 'Количество', 'Стоимость'].map(h2 => (
                      <th key={h2} style={{ padding: '8px 16px', textAlign: h2 === 'Стоимость' ? 'right' : 'left',
                        fontSize: '10px', color: 'var(--text-muted)', fontWeight: 500,
                        textTransform: 'uppercase', letterSpacing: '0.5px' }}>{h2}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border-row)' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                      <td style={{ padding: '9px 16px', color: 'var(--text-light)', fontWeight: 500 }}>{row.name || '—'}</td>
                      <td style={{ padding: '9px 16px', color: 'var(--text-muted)' }}>
                        {row.qty != null ? `${row.qty} шт.` : row.minutes != null ? `${row.minutes} мин.` : '—'}
                      </td>
                      <td style={{ padding: '9px 16px', textAlign: 'right', fontWeight: 600, color: '#10b981' }}>
                        {row.total != null ? fmtMoney(row.total) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            );
          })()}
        </TabPanel>
      </div>

      {/* ── Active clients + Account groups ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>

        {/* Active clients */}
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
          borderRadius: '12px', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '10px 16px', borderBottom: '1px solid var(--border-color)', background: 'var(--bg-dark)' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-light)' }}>
              Активные клиенты
            </span>
            <div style={{ display: 'flex', gap: '4px' }}>
              {['day', 'shift'].map(p => (
                <button key={p} onClick={() => setClientPeriod(p)}
                  style={{ padding: '3px 10px', borderRadius: '6px', fontSize: '11px', cursor: 'pointer',
                    fontFamily: 'inherit', border: `1px solid ${clientPeriod === p ? 'var(--accent)' : 'var(--border-color)'}`,
                    background: clientPeriod === p ? 'var(--accent-dim)' : 'transparent',
                    color: clientPeriod === p ? 'var(--accent)' : 'var(--text-muted)' }}>
                  {p === 'day' ? 'За день' : 'За смену'}
                </button>
              ))}
            </div>
          </div>
          <div style={{ overflow: 'auto', maxHeight: '220px' }}>
            {activeClients.length === 0 && clients.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                Нет активных клиентов
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-panel)' }}>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    {/* BUGFIX: columns were mislabeled. The cells below render the client's
                        deposit balance (deposit_money) and remaining play time (formatted_time),
                        NOT spending or total hours. Labels corrected to match the data. */}
                    {['Никнейм', 'Депозит', 'Остаток времени', 'Посл. посещение'].map(h2 => (
                      <th key={h2} style={{ padding: '8px 14px', textAlign: 'left',
                        fontSize: '10px', color: 'var(--text-muted)', fontWeight: 500,
                        textTransform: 'uppercase', letterSpacing: '0.4px', whiteSpace: 'nowrap' }}>{h2}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(activeClients.length > 0 ? activeClients : clients.slice(0, 10)).map(c => (
                    <tr key={c.id} style={{ borderBottom: '1px solid var(--border-row)' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                      <td style={{ padding: '8px 14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
                            background: 'linear-gradient(135deg,#6366f1,#a855f7)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: '#fff', fontWeight: 700, fontSize: '11px' }}>
                            {(c.username || '?')[0].toUpperCase()}
                          </div>
                          <span style={{ fontWeight: 500, color: 'var(--text-light)' }}>{c.username}</span>
                        </div>
                      </td>
                      <td style={{ padding: '8px 14px', color: '#f59e0b', fontWeight: 600 }}>
                        {Number(c.deposit || c.deposit_money || 0).toLocaleString('ru-RU')} сум
                      </td>
                      <td style={{ padding: '8px 14px', color: 'var(--text-muted)' }}>
                        {c.formatted_time || c.balance_formatted || '—'}
                      </td>
                      <td style={{ padding: '8px 14px', color: 'var(--text-muted)' }}>
                        {c.last_visit_at ? fmtDate(c.last_visit_at) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Account groups */}
        <TabPanel
          tabs={[
            { id: 'all',      label: 'Группы аккаунтов', count: allAccounts.length },
            { id: 'occupied', label: 'Занятые аккаунты', count: occupiedAccounts.length },
          ]}
          activeTab={accountTab} setActiveTab={setAccountTab}
          style={{ maxHeight: '290px' }}>
          {(() => {
            const rows = accountTab === 'occupied' ? occupiedAccounts : allAccounts;
            if (rows.length === 0) return (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                {accountTab === 'occupied' ? 'Нет занятых аккаунтов' : 'Аккаунты не настроены'}
              </div>
            );
            return (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                    {['Название ПК', 'Группа аккаунтов', 'Статус', 'Управление'].map((h2, i) => (
                      <th key={h2} style={{ padding: '8px 14px', textAlign: i === 3 ? 'right' : 'left',
                        fontSize: '10px', color: 'var(--text-muted)', fontWeight: 500,
                        textTransform: 'uppercase', letterSpacing: '0.4px' }}>{h2}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(a => (
                    <tr key={a.id} style={{ borderBottom: '1px solid var(--border-row)' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                      <td style={{ padding: '8px 14px', color: 'var(--text-muted)' }}>—</td>
                      <td style={{ padding: '8px 14px', fontWeight: 500, color: 'var(--text-light)' }}>
                        {a.platform || 'EPG'}
                      </td>
                      <td style={{ padding: '8px 14px' }}>
                        <span style={{ padding: '2px 8px', borderRadius: '999px', fontSize: '11px', fontWeight: 600,
                          background: a.in_use ? 'rgba(239,68,68,0.12)' : 'rgba(16,185,129,0.12)',
                          color: a.in_use ? '#ef4444' : '#10b981' }}>
                          {a.in_use ? 'Занят' : 'Свободен'}
                        </span>
                      </td>
                      <td style={{ padding: '8px 14px', textAlign: 'right' }}>
                        {a.in_use && (
                          <button style={{ padding: '3px 10px', borderRadius: '6px', fontSize: '11px',
                            border: '1px solid rgba(239,68,68,0.3)', background: 'rgba(239,68,68,0.08)',
                            color: '#ef4444', cursor: 'pointer', fontFamily: 'inherit' }}>
                            Освободить
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            );
          })()}
        </TabPanel>
      </div>
    </div>
  );
};

export default Dashboard;
