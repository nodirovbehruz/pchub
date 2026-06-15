import { useState, useEffect, useCallback } from 'react';
import {
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Area, AreaChart,
} from 'recharts';
import {
  Flag, LayoutGrid, Users, UserCheck, Monitor, Gamepad2, ShoppingBag,
  ArrowLeftRight, RefreshCw, Download, Calendar, Info, Clock,
  Wallet, Cpu, ArrowDownToLine, ArrowUpFromLine, PiggyBank,
} from 'lucide-react';
import { apiFetch } from '../api/client';

/* ── helpers ── */
const fmtRub = (v) => Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 2 }) + ' сум';
const fmtNum = (v) => Number(v || 0).toLocaleString('ru-RU');
const fmtDate = (iso) => { try { return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }); } catch { return iso; } };

/* ── Tabs ── */
const TABS = [
  { id: 'shifts',    label: 'Смены',                icon: Flag },
  { id: 'overview',  label: 'Обзорный',             icon: LayoutGrid },
  { id: 'clients',   label: 'Клиенты',              icon: Users },
  { id: 'visitors',  label: 'Посетители',           icon: UserCheck },
  { id: 'equipment', label: 'Занятость оборудования', icon: Monitor },
  { id: 'games',     label: 'Игры и приложения',    icon: Gamepad2 },
  { id: 'sales',     label: 'Продажи',              icon: ShoppingBag },
  { id: 'transfers', label: 'Межклубные переводы',  icon: ArrowLeftRight },
];

const PERIODS = [
  { id: 'week',    label: 'Неделя',  days: 7 },
  { id: 'month',   label: 'Месяц',   days: 30 },
  { id: 'quarter', label: 'Квартал', days: 90 },
  { id: 'year',    label: 'Год',     days: 365 },
];

/* date range helper */
const rangeForPeriod = (days) => {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - days + 1);
  // BUGFIX: use LOCAL date components, not toISOString() (UTC) — for UTC+5 an evening
  // request would otherwise send tomorrow's / a day-behind range, shifting revenue
  // into the wrong day.
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  return { from: iso(from), to: iso(to) };
};

/* ── Metric card (financial) ── */
const MetricCard = ({ icon: Icon, value, label, sub, subColor }) => (
  <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
    borderRadius: '12px', padding: '16px 18px', flex: 1, minWidth: '160px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
      <Icon size={15} color="var(--text-muted)" />
      <span style={{ fontSize: '20px', fontWeight: 700 }}>{value}</span>
      {sub && <span style={{ fontSize: '12px', fontWeight: 600, color: subColor || '#10b981' }}>{sub}</span>}
    </div>
    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{label}</div>
  </div>
);

/* ── Section card ── */
const Card = ({ title, info, extra, children }) => (
  <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
    borderRadius: '12px', padding: '18px' }}>
    {title && (
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '14px', fontWeight: 700 }}>{title}</span>
          {info && <Info size={13} color="var(--text-muted)" />}
        </div>
        {extra}
      </div>
    )}
    {children}
  </div>
);

/* ── Vertical bar chart with % labels (like SmartShell) ── */
const PctBars = ({ data, color = '#3b82f6', height = 220 }) => {
  const max = Math.max(...data.map(d => d.value), 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around',
      height, gap: '12px', paddingTop: '24px' }}>
      {data.map((d, i) => {
        const h = (d.value / max) * (height - 50);
        return (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, marginBottom: '6px', color: 'var(--text-main)' }}>
              {d.pct != null ? `${d.pct}%` : fmtRub(d.value)}
            </div>
            <div style={{ width: '100%', maxWidth: '90px', height: Math.max(h, 2),
              background: d.color || color, borderRadius: '6px 6px 0 0',
              transition: 'height 0.4s' }} />
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', textAlign: 'center' }}>
              {d.label}
            </div>
          </div>
        );
      })}
    </div>
  );
};

/* ════════════════════════════════════════════════════════════════════════
   OVERVIEW TAB
═══════════════════════════════════════════════════════════════════════ */
const OverviewTab = ({ data }) => {
  if (!data) return <Empty />;
  const f = data.financial || {};
  const rm = data.revenue_by_method || {};
  const sp = data.spending || {};
  const cl = data.clients || {};
  const vd = data.visit_distribution || [];

  const revenueBars = [
    { label: 'Наличные',    value: rm.cash,   pct: rm.total ? Math.round(rm.cash / rm.total * 100) : 0, color: '#93c5fd' },
    { label: 'Безналичные', value: rm.card,   pct: rm.total ? Math.round(rm.card / rm.total * 100) : 0, color: '#3b82f6' },
    { label: 'Онлайн',      value: rm.online, pct: rm.total ? Math.round(rm.online / rm.total * 100) : 0, color: '#bfdbfe' },
  ];
  const spendBars = [
    { label: 'Тарифы',  value: sp.tariffs,  pct: sp.total ? Math.round(sp.tariffs / sp.total * 100) : 0, color: '#bfdbfe' },
    { label: 'Товары',  value: sp.products, pct: sp.total ? Math.round(sp.products / sp.total * 100) : 0, color: '#bfdbfe' },
    { label: 'Услуги',  value: sp.services, pct: sp.total ? Math.round(sp.services / sp.total * 100) : 0, color: '#bfdbfe' },
  ];
  const visitBars = vd.map(v => ({ label: v.label, value: v.count, pct: v.pct, color: '#bfdbfe' }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Financial metrics */}
      <div>
        <div style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px' }}>Финансовые показатели</div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <MetricCard icon={Wallet}          value={fmtRub(f.revenue)}        label="Выручка" />
          <MetricCard icon={Cpu}             value={fmtRub(f.income_per_pc)}  label="Доход на 1 ПК" />
          <MetricCard icon={ArrowDownToLine} value={fmtRub(f.pko)}            label="Приходные ордера" />
          <MetricCard icon={ArrowUpFromLine} value={fmtRub(f.rko)}            label="Расходные ордера" />
          <MetricCard icon={PiggyBank}       value={fmtRub(f.deposit_topups)} label="Пополнение депозита"
            sub={f.deposit_pct ? `${f.deposit_pct}%` : undefined} subColor="#3b82f6" />
        </div>
      </div>

      {/* Revenue + Client spending */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <Card title="Выручка" info>
          <PctBars data={revenueBars.map(b => ({ ...b, pct: undefined }))} />
          <div style={{ display: 'flex', justifyContent: 'space-around', marginTop: '4px' }}>
            {revenueBars.map(b => (
              <div key={b.label} style={{ fontSize: '11px', color: '#3b82f6', fontWeight: 600 }}>{b.pct}%</div>
            ))}
          </div>
        </Card>
        <Card title="Распределение расходов клиентов" info>
          <PctBars data={spendBars} />
        </Card>
      </div>

      {/* Bonuses + Clients */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Bonuses */}
        <div>
          <div style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px' }}>Бонусы</div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <MetricCard icon={PiggyBank} value={fmtNum(data.bonuses?.total)} label="Бонусный баланс клиентов" />
          </div>
        </div>
        {/* Clients */}
        <div>
          <div style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px' }}>Клиенты</div>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <MetricCard icon={Users}     value={`${fmtNum(cl.unique)} чел.`}   label="Уникальные клиенты" />
            <MetricCard icon={UserCheck} value={`${fmtNum(cl.new)} чел.`}      label="Новые клиенты"
              sub={`${cl.new_pct}%`} subColor="#3b82f6" />
            <MetricCard icon={Users}     value={`${fmtNum(cl.returning)} чел.`} label="Вернувшиеся клиенты"
              sub={`${cl.returning_pct}%`} subColor="#3b82f6" />
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <MetricCard icon={Monitor} value={`${fmtNum(cl.guest_sessions)} шт.`} label="Гостевые сеансы" />
          <MetricCard icon={Wallet}  value={fmtRub(cl.arpu)} label="Средний чек на клиента, ARPU" />
        </div>
        <Card title="Распределение клиентов по количеству визитов" info>
          {visitBars.length === 0 || visitBars.every(b => b.value === 0)
            ? <Empty small />
            : <PctBars data={visitBars} height={200} />}
        </Card>
      </div>
    </div>
  );
};

/* ════════════════════════════════════════════════════════════════════════
   VISITORS TAB
═══════════════════════════════════════════════════════════════════════ */
const VisitorsTab = ({ data, onExport }) => {
  if (!data) return <Empty />;
  const s = data.summary || {};
  const daily = (data.daily || []).map(d => ({ ...d, dateLabel: fmtDate(d.date) }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <Card
        title="Посетители"
        extra={
          <button className="btn btn-secondary" onClick={onExport}
            style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Download size={13} /> Экспорт в CSV
          </button>
        }>
        {/* Summary row */}
        <div style={{ display: 'flex', gap: '32px', marginBottom: '20px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Всего</div>
            <div style={{ fontSize: '22px', fontWeight: 700 }}>{fmtNum(s.total_visitors)} чел.</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              <span style={{ color: '#ef4444' }}>Макс. {s.peak}</span> · <span style={{ color: '#3b82f6' }}>Мин. {s.low}</span>
            </div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Клиенты</div>
            <div style={{ fontSize: '22px', fontWeight: 700 }}>{fmtNum(s.total_clients)} чел.</div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Сеансов</div>
            <div style={{ fontSize: '22px', fontWeight: 700 }}>{fmtNum(s.total_sessions)} шт.</div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Гости</div>
            <div style={{ fontSize: '22px', fontWeight: 700 }}>{fmtNum(s.total_guests)} чел.</div>
          </div>
        </div>

        {/* Area chart */}
        {daily.length === 0 ? <Empty small /> : (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={daily}>
              <defs>
                <linearGradient id="visGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="dateLabel" axisLine={false} tickLine={false}
                tick={{ fill: 'var(--text-muted)', fontSize: 10 }} minTickGap={20} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 11 }} width={36} />
              <Tooltip contentStyle={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
                borderRadius: '8px', fontSize: '12px' }} />
              <Area type="monotone" dataKey="visitors" name="Посетители" stroke="#3b82f6"
                fill="url(#visGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </Card>

      {/* Daily table */}
      <Card title="">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              {['Дата', 'Клиенты', 'Гости', 'Посетители', 'Сеансы'].map(c => (
                <th key={c} style={{ padding: '10px 14px', textAlign: c === 'Дата' ? 'left' : 'right',
                  fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {daily.slice().reverse().map(d => (
              <tr key={d.date} style={{ borderBottom: '1px solid var(--border-row)' }}>
                <td style={{ padding: '9px 14px' }}>{new Date(d.date).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric', weekday: 'short' })}</td>
                <td style={{ padding: '9px 14px', textAlign: 'right' }}>{d.clients} чел.</td>
                <td style={{ padding: '9px 14px', textAlign: 'right' }}>{d.guests} чел.</td>
                <td style={{ padding: '9px 14px', textAlign: 'right', fontWeight: 600 }}>{d.visitors} чел.</td>
                <td style={{ padding: '9px 14px', textAlign: 'right', color: 'var(--text-muted)' }}>{d.sessions} шт.</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

const fmtHours = (mins) => {
  const m = Number(mins || 0);
  const h = Math.floor(m / 60);
  const rest = m % 60;
  return h > 0 ? `${h} ч. ${rest} мин.` : `${rest} мин.`;
};
const fmtHoursDec = (h) => `${Number(h || 0).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} ч.`;

/* ── Simple sortable table ── */
const DataTable = ({ columns, rows, emptyText = 'Нет данных за выбранный период' }) => {
  const [sort, setSort] = useState({ key: null, dir: 1 });
  if (!rows || rows.length === 0) return <Empty text={emptyText} />;
  const sorted = sort.key
    ? [...rows].sort((a, b) => {
        const av = a[sort.key], bv = b[sort.key];
        if (typeof av === 'number') return (av - bv) * sort.dir;
        return String(av ?? '').localeCompare(String(bv ?? '')) * sort.dir;
      })
    : rows;
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
      <thead>
        <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
          {columns.map(c => (
            <th key={c.key} onClick={() => c.sortable !== false && setSort(s => ({ key: c.key, dir: s.key === c.key ? -s.dir : 1 }))}
              style={{ padding: '10px 14px', textAlign: c.align || 'left', fontSize: '10px',
                color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
                cursor: c.sortable !== false ? 'pointer' : 'default', whiteSpace: 'nowrap', userSelect: 'none' }}>
              {c.label} {sort.key === c.key ? (sort.dir === 1 ? '↑' : '↓') : (c.sortable !== false ? '↕' : '')}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sorted.map((r, i) => (
          <tr key={r.id ?? r.user_id ?? r.pc_id ?? i} style={{ borderBottom: '1px solid var(--border-row)' }}>
            {columns.map(c => (
              <td key={c.key} style={{ padding: '10px 14px', textAlign: c.align || 'left',
                color: c.muted ? 'var(--text-muted)' : 'var(--text-main)', fontWeight: c.bold ? 700 : 400, whiteSpace: 'nowrap' }}>
                {c.render ? c.render(r) : r[c.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

/* ════════════════════════════════════════════════════════════════════════
   SHIFTS TAB
═══════════════════════════════════════════════════════════════════════ */
const ShiftsTab = ({ data }) => {
  if (!data) return <Empty />;
  const s = data.summary || {};
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <MetricCard icon={Clock}    value={fmtHours(s.worked_minutes)} label="Отработано" />
        <MetricCard icon={Wallet}   value={fmtRub(s.revenue)}          label="Выручка" />
        <MetricCard icon={ShoppingBag} value={fmtRub(s.products)}      label="Выручка с товаров" />
        <MetricCard icon={ShoppingBag} value={fmtRub(s.services)}      label="Выручка с услуг" />
        <MetricCard icon={PiggyBank} value={fmtNum(s.bonus)}           label="Бонусов" />
        <MetricCard icon={ArrowUpFromLine} value={fmtRub(s.refunds)}   label="Возвратов" />
      </div>
      <Card title="">
        <DataTable
          columns={[
            { key: 'employee', label: 'Сотрудник', bold: true },
            { key: 'shifts_count', label: 'Кол-во смен', align: 'right' },
            { key: 'worked_minutes', label: 'Отработано', align: 'right', render: r => fmtHours(r.worked_minutes) },
            { key: 'revenue', label: 'Выручка', align: 'right', render: r => fmtRub(r.revenue) },
            { key: 'products', label: 'Товары', align: 'right', render: r => fmtRub(r.products) },
            { key: 'services', label: 'Услуги', align: 'right', render: r => fmtRub(r.services) },
            { key: 'bonus', label: 'Бонусов', align: 'right', render: r => fmtNum(r.bonus) },
            { key: 'refunds', label: 'Возвратов', align: 'right', render: r => fmtRub(r.refunds) },
          ]}
          rows={data.rows}
        />
      </Card>
    </div>
  );
};

/* ════════════════════════════════════════════════════════════════════════
   CLIENTS TAB
═══════════════════════════════════════════════════════════════════════ */
const ClientsTab = ({ data, search, setSearch, page, setPage }) => {
  return (
    <Card title="" extra={
      <div style={{ position: 'relative' }}>
        <input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}
          placeholder="Найти клиента"
          style={{ height: '32px', padding: '0 12px', width: '220px', background: 'var(--bg-input)',
            border: '1px solid var(--border-input)', borderRadius: '8px', color: 'var(--text-main)',
            fontSize: '13px', fontFamily: 'inherit' }} />
      </div>
    }>
      <DataTable
        columns={[
          { key: 'client', label: 'Клиент', bold: true,
            render: r => <div><div style={{ fontWeight: 600 }}>{r.client}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{r.username}</div></div> },
          { key: 'registered_at', label: 'Регистрация', muted: true,
            render: r => r.registered_at ? new Date(r.registered_at).toLocaleDateString('ru-RU') : '—' },
          { key: 'balance', label: 'Баланс', align: 'right', render: r => fmtRub(r.balance) },
          { key: 'discount', label: 'Скидка', align: 'right', render: r => `${r.discount}%` },
          { key: 'spent_total', label: 'Траты за период', align: 'right', bold: true, render: r => fmtRub(r.spent_total) },
          { key: 'spent_tariffs', label: 'На тарифы', align: 'right', render: r => fmtRub(r.spent_tariffs) },
          { key: 'spent_shop', label: 'В магазине', align: 'right', render: r => fmtRub(r.spent_shop) },
          { key: 'avg_check', label: 'Средний чек', align: 'right', render: r => fmtRub(r.avg_check) },
        ]}
        rows={data?.rows}
      />
      {data && data.pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '6px', marginTop: '16px' }}>
          {Array.from({ length: data.pages }, (_, i) => i + 1).slice(0, 10).map(p => (
            <button key={p} onClick={() => setPage(p)}
              style={{ width: '32px', height: '32px', borderRadius: '7px', cursor: 'pointer', border: 'none',
                fontFamily: 'inherit', fontSize: '12px',
                background: page === p ? 'var(--accent)' : 'var(--hover-overlay)',
                color: page === p ? '#fff' : 'var(--text-muted)' }}>{p}</button>
          ))}
        </div>
      )}
    </Card>
  );
};

/* ════════════════════════════════════════════════════════════════════════
   EQUIPMENT TAB
═══════════════════════════════════════════════════════════════════════ */
const EquipmentTab = ({ data }) => {
  if (!data) return <Empty />;
  const s = data.summary || {};
  const bars = (data.rows || []).slice(0, 20).map(r => ({ label: r.pc_name, value: r.revenue, color: '#3b82f6' }));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <Card title="Занятость оборудования за выбранный период" info>
        <div style={{ display: 'flex', gap: '32px', marginBottom: '20px', flexWrap: 'wrap' }}>
          {[
            { v: fmtHoursDec(s.total_machine_hours), l: 'Всего машиночасов' },
            { v: fmtHoursDec(s.busy_hours), l: 'Общее время занятости', sub: s.busy_pct ? `${s.busy_pct}%` : null },
            { v: `${fmtNum(s.sessions)} шт.`, l: 'Общее количество сессий' },
            { v: fmtHoursDec(s.avg_session), l: 'Среднее время сессии' },
            { v: fmtRub(s.revenue), l: 'Выручка' },
          ].map((m, i) => (
            <div key={i}>
              <div style={{ fontSize: '22px', fontWeight: 700 }}>{m.v}
                {m.sub && <span style={{ fontSize: '12px', color: '#3b82f6', marginLeft: '6px' }}>{m.sub}</span>}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{m.l}</div>
            </div>
          ))}
        </div>
        {bars.length > 0 && bars.some(b => b.value > 0)
          ? <PctBars data={bars.map(b => ({ ...b, pct: undefined }))} height={240} />
          : <Empty small />}
      </Card>
      <Card title="">
        <DataTable
          columns={[
            { key: 'pc_name', label: 'Игровое место', bold: true },
            { key: 'zone', label: 'Зал', muted: true },
            { key: 'busy_hours', label: 'Общая занятость', align: 'right', render: r => <span>{fmtHoursDec(r.busy_hours)} <span style={{ color: '#3b82f6', fontSize: '11px' }}>{r.busy_pct}%</span></span> },
            { key: 'avg_session', label: 'Ср. время сессии', align: 'right', render: r => fmtHoursDec(r.avg_session) },
            { key: 'sessions', label: 'Всего сессий', align: 'right', render: r => `${r.sessions} шт.` },
            { key: 'revenue', label: 'Выручка', align: 'right', bold: true, render: r => fmtRub(r.revenue) },
          ]}
          rows={data.rows}
        />
      </Card>
    </div>
  );
};

/* ════════════════════════════════════════════════════════════════════════
   SALES TAB
═══════════════════════════════════════════════════════════════════════ */
const CAT_COLORS = {
  'Пополнение депозита': '#8b5cf6',
  'Тариф': '#3b82f6',
  'Товар': '#10b981',
  'Услуга': '#f59e0b',
  'Бонус': '#ec4899',
};
const SalesTab = ({ data }) => {
  if (!data) return <Empty />;
  const s = data.summary || {};
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ fontSize: '15px', fontWeight: 700 }}>Сводные данные</div>
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <MetricCard icon={PiggyBank}   value={fmtRub(s.deposit_topups)} label={`Пополнений депозитов: ${s.deposit_count}`} />
        <MetricCard icon={Clock}       value={fmtRub(s.tariffs_sum)}    label={`Продано тарифов: ${s.tariffs_sold}`} />
        <MetricCard icon={ShoppingBag} value={fmtRub(s.products_sum)}   label={`Продано товаров: ${s.products_sold}`} />
        <MetricCard icon={PiggyBank}   value={fmtRub(s.bonus_topups)}   label={`Бонусных пополнений: ${s.bonus_count}`} />
      </div>
      <Card title="">
        <DataTable
          columns={[
            { key: 'name', label: 'Название позиции', bold: true },
            { key: 'category', label: 'Категория',
              render: r => <span style={{ padding: '2px 8px', borderRadius: '999px', fontSize: '11px', fontWeight: 600,
                background: (CAT_COLORS[r.category] || '#6b7280') + '22', color: CAT_COLORS[r.category] || '#6b7280' }}>{r.category}</span> },
            { key: 'qty', label: 'Продано', align: 'right', render: r => `${r.qty} шт.` },
            { key: 'sum', label: 'Сумма', align: 'right', bold: true, render: r => fmtRub(r.sum) },
            { key: 'avg', label: 'Ср. стоимость', align: 'right', render: r => fmtRub(r.avg) },
            { key: 'cancels', label: 'Кол-во отмен', align: 'right', muted: true, render: r => r.cancels },
          ]}
          rows={data.rows}
        />
      </Card>
    </div>
  );
};

/* ════════════════════════════════════════════════════════════════════════
   GAMES TAB
═══════════════════════════════════════════════════════════════════════ */
const GamesTab = ({ data }) => {
  if (!data) return <Empty />;
  return (
    <Card title={`Игры и приложения (${data.total_games})`} info>
      <DataTable
        columns={[
          { key: 'name', label: 'Название', bold: true },
          { key: 'installs', label: 'Установлено на ПК', align: 'right', render: r => `${r.installs} шт.` },
        ]}
        rows={data.rows}
        emptyText="Нет данных об установленных играх"
      />
    </Card>
  );
};

/* ════════════════════════════════════════════════════════════════════════
   TRANSFERS TAB
═══════════════════════════════════════════════════════════════════════ */
const TransfersTab = ({ data }) => {
  if (!data) return <Empty />;
  return (
    <Card title="Межклубные переводы" info>
      <DataTable
        columns={[
          { key: 'date', label: 'Дата', render: r => new Date(r.date).toLocaleString('ru-RU') },
          { key: 'object', label: 'Описание', bold: true },
          { key: 'operator', label: 'Оператор', muted: true },
        ]}
        rows={data.rows}
        emptyText="Межклубных переводов за период нет"
      />
    </Card>
  );
};

/* ── Empty ── */
const Empty = ({ small, text }) => (
  <div style={{ padding: small ? '30px' : '60px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
    {text || 'Нет данных за выбранный период'}
  </div>
);

/* ════════════════════════════════════════════════════════════════════════
   MAIN
═══════════════════════════════════════════════════════════════════════ */
/* tab → endpoint path */
const TAB_ENDPOINT = {
  overview:  'analytics/',
  visitors:  'analytics/visitors/',
  shifts:    'analytics/shifts/',
  clients:   'analytics/clients/',
  equipment: 'analytics/equipment/',
  sales:     'analytics/sales/',
  games:     'analytics/games/',
  transfers: 'analytics/transfers/',
};

const Analytics = () => {
  const [tab, setTab]         = useState('overview');
  const [period, setPeriod]   = useState('month');
  const [tabData, setTabData] = useState({}); // { [tab]: data }
  const [loading, setLoading] = useState(false);
  const [search, setSearch]   = useState('');
  const [page, setPage]       = useState(1);
  const clubId = localStorage.getItem('active_club_id');

  const range = rangeForPeriod(PERIODS.find(p => p.id === period)?.days || 30);

  const load = useCallback(async (which = tab) => {
    if (!clubId) return;
    setLoading(true);
    const r = rangeForPeriod(PERIODS.find(p => p.id === period)?.days || 30);
    const ep = TAB_ENDPOINT[which] || 'analytics/';
    let url = `/api/v1/billing/${ep}?club=${clubId}&from=${r.from}&to=${r.to}`;
    if (which === 'clients') url += `&search=${encodeURIComponent(search)}&page=${page}`;
    try {
      const data = await apiFetch(url, { noCache: true }).catch(() => null);
      setTabData(prev => ({ ...prev, [which]: data }));
    } finally {
      setLoading(false);
    }
  }, [clubId, period, tab, search, page]);

  // Reload when tab / period / clients-search / clients-page change
  useEffect(() => { load(tab); }, [tab, period]); // eslint-disable-line
  useEffect(() => { if (tab === 'clients') load('clients'); }, [search, page]); // eslint-disable-line

  const exportVisitors = () => {
    const v = tabData.visitors;
    if (!v?.daily) return;
    const headers = ['Дата', 'Клиенты', 'Гости', 'Посетители', 'Сеансы'];
    const lines = [headers.join(';'),
      ...v.daily.map(d => [d.date, d.clients, d.guests, d.visitors, d.sessions].join(';'))];
    const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `visitors_${range.from}_${range.to}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const exportCSV = (rows, headers, keys, name) => {
    if (!rows?.length) return;
    const lines = [headers.join(';'), ...rows.map(r => keys.map(k => r[k]).join(';'))];
    const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `${name}_${range.from}_${range.to}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ padding: '0 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700 }}>Аналитика</h2>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border-color)', overflowX: 'auto', paddingBottom: '0' }}>
        {TABS.map(t => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '9px 14px',
                background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit',
                fontSize: '13px', fontWeight: 500, whiteSpace: 'nowrap', marginBottom: '-1px',
                borderBottom: `2px solid ${active ? 'var(--accent)' : 'transparent'}`,
                color: active ? 'var(--text-main)' : 'var(--text-muted)' }}>
              <Icon size={14} /> {t.label}
            </button>
          );
        })}
      </div>

      {/* Period selector */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '2px', padding: '2px', background: 'var(--bg-panel)',
          borderRadius: '9px', border: '1px solid var(--border-color)' }}>
          {PERIODS.map(p => (
            <button key={p.id} onClick={() => setPeriod(p.id)}
              style={{ padding: '6px 16px', borderRadius: '7px', fontSize: '12px', cursor: 'pointer',
                border: 'none', fontFamily: 'inherit', fontWeight: 500,
                background: period === p.id ? 'var(--accent)' : 'transparent',
                color: period === p.id ? '#fff' : 'var(--text-muted)' }}>
              {p.label}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px',
          background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: '8px',
          fontSize: '12px', color: 'var(--text-muted)' }}>
          <Calendar size={13} /> {fmtDate(range.from)} — {fmtDate(range.to)}
        </div>
        <button className="btn btn-primary" onClick={() => load(tab)} disabled={loading}
          style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <RefreshCw size={13} style={loading ? { animation: 'spin 1s linear infinite' } : undefined} />
          {loading ? 'Загрузка…' : 'Сгенерировать'}
        </button>
      </div>

      {/* Per-tab export */}
      {['shifts', 'clients', 'equipment', 'sales'].includes(tab) && tabData[tab]?.rows?.length > 0 && (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary"
            style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px' }}
            onClick={() => {
              const rows = tabData[tab].rows;
              const keys = Object.keys(rows[0]).filter(k => !['user_id','pc_id','id','username'].includes(k));
              exportCSV(rows, keys, keys, tab);
            }}>
            <Download size={13} /> Экспорт в CSV
          </button>
        </div>
      )}

      {/* Tab content */}
      {loading ? (
        <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>Загрузка аналитики…</div>
      ) : (
        <>
          {tab === 'overview'  && <OverviewTab data={tabData.overview} />}
          {tab === 'visitors'  && <VisitorsTab data={tabData.visitors} onExport={exportVisitors} />}
          {tab === 'shifts'    && <ShiftsTab data={tabData.shifts} />}
          {tab === 'clients'   && <ClientsTab data={tabData.clients} search={search} setSearch={setSearch} page={page} setPage={setPage} />}
          {tab === 'equipment' && <EquipmentTab data={tabData.equipment} />}
          {tab === 'games'     && <GamesTab data={tabData.games} />}
          {tab === 'sales'     && <SalesTab data={tabData.sales} />}
          {tab === 'transfers' && <TransfersTab data={tabData.transfers} />}
        </>
      )}
    </div>
  );
};

export default Analytics;
