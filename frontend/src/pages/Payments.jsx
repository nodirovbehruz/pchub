import { useState, useEffect, useCallback } from 'react';
import {
  Wallet, RefreshCw, Search, ArrowDownToLine, ArrowUpFromLine,
  X, RotateCcw, Download, FileText, Clock, ShoppingBag,
  CreditCard, Timer, TrendingUp,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

/* ── helpers ─────────────────────────────────────────────────────────────── */
const fmtMoney = (v) =>
  Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 2 }) + ' сум';

const fmtDateTime = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return '—'; }
};

const fmtMins = (m) => {
  if (!m || m <= 0) return null;
  const h = Math.floor(m / 60), min = m % 60;
  return h > 0 ? `${h}ч ${min > 0 ? min + 'м' : ''}` : `${min}м`;
};

const METHOD = {
  cash:     { label: 'Наличные', color: '#10b981' },
  card:     { label: 'Карта',    color: '#3b82f6' },
  balance:  { label: 'Депозит',  color: '#f59e0b' },
  deposit:  { label: 'Депозит',  color: '#f59e0b' },
  transfer: { label: 'Перевод',  color: '#a78bfa' },
  bonus:    { label: 'Бонусы',   color: '#ec4899' },
};

/* Категория из note + minutes_added */
const getCategory = (p) => {
  const note = p.note || '';
  if (note.includes('[POSTPAID]'))      return { label: 'Постоплата',      color: '#f59e0b', icon: Timer };
  if (note.includes('[POS]'))           return { label: 'Магазин',          color: '#8b5cf6', icon: ShoppingBag };
  if (note.includes('[CLIENT]'))        return { label: 'Тариф (клиент)',   color: '#6366f1', icon: CreditCard };
  if ((p.minutes_added || 0) > 0)       return { label: 'Тариф / Время',   color: '#6366f1', icon: Clock };
  return                                       { label: 'Пополнение',       color: '#10b981', icon: TrendingUp };
};

/* Статус */
const isRefunded = (p) => (p.note || '').includes('[REFUNDED]');

/* Очистить note для отображения */
const cleanNote = (note = '') =>
  note
    .replace('[REFUNDED]', '').replace('[DEPOSIT]', '').replace('[POS]', '')
    .replace('[CLIENT]', '').replace('[POSTPAID]', '')
    .replace(/\[СКИДКА\s*[\d.]+%\]/, '').trim() || '—';

/* CSV export */
const exportCSV = (rows) => {
  const headers = ['ID', 'Дата', 'Клиент', 'Способ', 'Категория', 'Сумма', 'Статус', 'Примечание'];
  const lines = [headers.join(';'),
    ...rows.map(p => [
      p.id,
      fmtDateTime(p.created_at),
      p.user_username || '—',
      METHOD[p.payment_method]?.label || p.payment_method,
      getCategory(p).label,
      Number(p.amount_paid || 0).toFixed(2),
      isRefunded(p) ? 'ВОЗВРАТ' : 'АКТИВЕН',
      `"${cleanNote(p.note)}"`,
    ].join(';'))
  ];
  const bom = '﻿';
  const blob = new Blob([bom + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url;
  a.download = `payments_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click(); URL.revokeObjectURL(url);
};

/* ── Receipt modal ────────────────────────────────────────────────────────── */
const ReceiptModal = ({ payment: p, onClose, onRefund }) => {
  const cat = getCategory(p);
  const refunded = isRefunded(p);
  const method = METHOD[p.payment_method] || { label: p.payment_method, color: 'var(--text-muted)' };
  const CatIcon = cat.icon;

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: '16px', padding: '28px',
        width: '420px', maxWidth: '92vw', border: '1px solid var(--border-color)' }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={18} color="var(--accent)" />
            <span style={{ fontWeight: 700, fontSize: '15px' }}>Чек #{p.id}</span>
            {refunded && (
              <span style={{ fontSize: '11px', fontWeight: 700, padding: '2px 8px',
                borderRadius: '999px', background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}>
                ВОЗВРАТ
              </span>
            )}
          </div>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>

        {/* Rows */}
        {[
          { label: 'Дата и время', value: fmtDateTime(p.created_at) },
          { label: 'Клиент', value: p.user_username || 'Гость' },
          { label: 'Оператор', value: p.admin_username || '—' },
        ].map(r => (
          <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between',
            padding: '9px 0', borderBottom: '1px solid var(--border-row)', fontSize: '13px' }}>
            <span style={{ color: 'var(--text-muted)' }}>{r.label}</span>
            <span style={{ fontWeight: 500 }}>{r.value}</span>
          </div>
        ))}

        {/* Category */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '9px 0', borderBottom: '1px solid var(--border-row)', fontSize: '13px' }}>
          <span style={{ color: 'var(--text-muted)' }}>Категория</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px',
            padding: '2px 10px', borderRadius: '999px', fontSize: '12px', fontWeight: 600,
            background: cat.color + '22', color: cat.color }}>
            <CatIcon size={12} /> {cat.label}
          </span>
        </div>

        {/* Method */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '9px 0', borderBottom: '1px solid var(--border-row)', fontSize: '13px' }}>
          <span style={{ color: 'var(--text-muted)' }}>Способ оплаты</span>
          <span style={{ padding: '2px 10px', borderRadius: '999px', fontSize: '12px', fontWeight: 600,
            background: method.color + '22', color: method.color }}>{method.label}</span>
        </div>

        {/* Minutes (if billing) */}
        {(p.minutes_added > 0) && (
          <div style={{ display: 'flex', justifyContent: 'space-between',
            padding: '9px 0', borderBottom: '1px solid var(--border-row)', fontSize: '13px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Игровое время</span>
            <span style={{ fontWeight: 600, color: '#6366f1' }}>+{fmtMins(p.minutes_added)}</span>
          </div>
        )}

        {/* Note */}
        {cleanNote(p.note) !== '—' && (
          <div style={{ display: 'flex', justifyContent: 'space-between',
            padding: '9px 0', borderBottom: '1px solid var(--border-row)', fontSize: '13px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Примечание</span>
            <span style={{ maxWidth: '220px', textAlign: 'right', color: 'var(--text-muted)', fontSize: '12px' }}>
              {cleanNote(p.note)}
            </span>
          </div>
        )}

        {/* Total */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '14px 0 4px', fontSize: '15px', fontWeight: 700 }}>
          <span>Итого</span>
          <span style={{ fontSize: '20px', color: refunded ? '#ef4444' : '#10b981' }}>
            {refunded ? '−' : ''}{fmtMoney(p.amount_paid)}
          </span>
        </div>

        {/* Refund button */}
        {!refunded && (
          <button
            className="btn btn-secondary"
            style={{ width: '100%', marginTop: '16px', display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: '6px', color: '#ef4444', borderColor: 'rgba(239,68,68,0.3)' }}
            onClick={() => { onClose(); onRefund(p); }}>
            <RotateCcw size={14} /> Отменить платёж
          </button>
        )}
      </div>
    </div>
  );
};

/* ── Main ─────────────────────────────────────────────────────────────────── */
const Payments = () => {
  const { toast } = useToast();
  const [payments, setPayments]       = useState([]);
  const [cashOrders, setCashOrders]   = useState([]);
  const [loading, setLoading]         = useState(true);
  const [search, setSearch]           = useState('');
  const [filterMethod, setFilterMethod] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [shiftOnly, setShiftOnly]     = useState(false);
  const [currentShift, setCurrentShift] = useState(null);
  const [orderModal, setOrderModal]   = useState(null);
  const [orderForm, setOrderForm]     = useState({ amount: '', comment: '' });
  const [activeTab, setActiveTab]     = useState('payments');
  const [receiptPayment, setReceiptPayment] = useState(null);

  const clubId = localStorage.getItem('active_club_id');

  const load = useCallback(async () => {
    if (!clubId) return;
    setLoading(true);
    try {
      const [paymentsJson, cashJson, shiftJson] = await Promise.all([
        apiFetch(`/api/v1/billing/admin/payments/?club=${clubId}`).catch(() => []),
        apiFetch(`/api/v1/billing/cash-orders/?club=${clubId}`).catch(() => []),
        apiFetch(`/api/v1/billing/shifts/current/`).catch(() => null),
      ]);
      setPayments(paymentsJson.results || paymentsJson || []);
      setCashOrders(cashJson.results || cashJson || []);
      if (shiftJson?.is_active && shiftJson.shift) setCurrentShift(shiftJson.shift);
      else setCurrentShift(null);
    } finally {
      setLoading(false);
    }
  }, [clubId]);

  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, [load]);

  /* ── Filters ── */
  const CATEGORIES = [
    { id: '',          label: 'Все' },
    { id: 'tariff',    label: 'Тариф / Время' },
    { id: 'shop',      label: 'Магазин' },
    { id: 'topup',     label: 'Пополнение' },
    { id: 'postpaid',  label: 'Постоплата' },
  ];

  const matchCategory = (p) => {
    if (!filterCategory) return true;
    const note = p.note || '';
    if (filterCategory === 'shop')     return note.includes('[POS]');
    if (filterCategory === 'postpaid') return note.includes('[POSTPAID]');
    if (filterCategory === 'tariff')   return (p.minutes_added > 0) && !note.includes('[POSTPAID]') && !note.includes('[POS]');
    if (filterCategory === 'topup')    return !note.includes('[POS]') && !note.includes('[POSTPAID]') && !(p.minutes_added > 0);
    return true;
  };

  const shiftStart = currentShift?.opened_at ? new Date(currentShift.opened_at) : null;

  const filtered = payments.filter(p => {
    const q = search.toLowerCase();
    if (q && !(p.user_username || '').toLowerCase().includes(q)
          && !String(p.id).includes(q)
          && !(p.note || '').toLowerCase().includes(q)) return false;
    if (filterMethod && p.payment_method !== filterMethod) return false;
    if (!matchCategory(p)) return false;
    if (shiftOnly && shiftStart && new Date(p.created_at) < shiftStart) return false;
    return true;
  });

  /* ── Totals (active only) ── */
  const active = filtered.filter(p => !isRefunded(p));
  const totalCash = active.filter(p => p.payment_method === 'cash').reduce((s, p) => s + Number(p.amount_paid || 0), 0);
  const totalCard = active.filter(p => p.payment_method === 'card').reduce((s, p) => s + Number(p.amount_paid || 0), 0);
  const totalAll  = active.reduce((s, p) => s + Number(p.amount_paid || 0), 0);

  /* ── Refund ── */
  const refundPayment = async (payment) => {
    const isPos = (payment.note || '').includes('[POS]');
    const isDepositPos = isPos && (payment.note || '').includes('[DEPOSIT]');
    const msg = isPos
      ? `Вернуть платёж #${payment.id} (${fmtMoney(payment.amount_paid)})?\n• Товары вернутся на склад\n` +
        (isDepositPos ? '• Сумма вернётся на депозит клиента' : '• Выдайте сдачу вручную')
      : `Отменить платёж #${payment.id}?`;
    if (!window.confirm(msg)) return;
    try {
      const res = await apiFetch(`/api/v1/billing/admin/payments/${payment.id}/refund/`,
        { method: 'POST', body: JSON.stringify({ club: clubId }) });
      let m = 'Платёж отменён';
      if (res.restored_stock?.length) m += ` · Склад восстановлен (${res.restored_stock.length} поз.)`;
      if (res.deposit_returned) m += ` · Депозит +${fmtMoney(res.deposit_returned)}`;
      toast(m, { type: 'success' }); load();
    } catch (e) { toast('Ошибка: ' + (e.message || ''), { type: 'error' }); }
  };

  /* ── Cash order ── */
  const createCashOrder = async () => {
    const amount = parseFloat(orderForm.amount);
    if (!amount || amount <= 0) { toast('Введите сумму', { type: 'warning' }); return; }
    try {
      await apiFetch('/api/v1/billing/cash-orders/', {
        method: 'POST',
        body: JSON.stringify({ type: orderModal, amount, comment: orderForm.comment }),
      });
      toast(`${orderModal === 'pko' ? 'ПКО' : 'РКО'} на ${fmtMoney(amount)}`, { type: 'success' });
      setOrderModal(null); setOrderForm({ amount: '', comment: '' }); load();
    } catch (e) { toast('Ошибка: ' + (e.message || ''), { type: 'error' }); }
  };

  /* ── iStyle ── */
  const iStyle = { height: '34px', padding: '0 12px',
    background: 'var(--bg-input)', border: '1px solid var(--border-input)',
    borderRadius: '8px', color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit' };

  return (
    <div style={{ padding: '0 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
        <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700 }}>Платежи</h2>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button className="btn btn-secondary"
            onClick={() => exportCSV(filtered)}
            style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Download size={13} /> Экспорт CSV
          </button>
          <button className="btn btn-secondary"
            onClick={() => setOrderModal('pko')}
            style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <ArrowDownToLine size={13} /> ПКО
          </button>
          <button className="btn btn-secondary"
            onClick={() => setOrderModal('rko')}
            style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <ArrowUpFromLine size={13} /> РКО
          </button>
          <button className="btn btn-secondary" onClick={load} disabled={loading}>
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        {[
          { label: shiftOnly ? 'За смену (фильтр)' : 'Итого (фильтр)', value: fmtMoney(totalAll), color: '#10b981' },
          { label: 'Наличные',   value: fmtMoney(totalCash), color: '#10b981' },
          { label: 'Карта',      value: fmtMoney(totalCard), color: '#3b82f6' },
        ].map(c => (
          <div key={c.label} style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
            borderRadius: '12px', padding: '14px 18px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>{c.label}</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: c.color }}>{c.value}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border-color)' }}>
        {[
          { id: 'payments',   label: `Платежи (${payments.length})` },
          { id: 'cashorders', label: `Ордера (${cashOrders.length})` },
        ].map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            style={{ padding: '8px 16px', background: 'none', border: 'none', cursor: 'pointer',
              fontFamily: 'inherit', fontSize: '13px', fontWeight: 500, marginBottom: '-1px',
              borderBottom: `2px solid ${activeTab === t.id ? 'var(--accent)' : 'transparent'}`,
              color: activeTab === t.id ? 'var(--text-main)' : 'var(--text-muted)' }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Filters — payments tab */}
      {activeTab === 'payments' && (
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Search */}
          <div style={{ position: 'relative' }}>
            <Search size={13} style={{ position: 'absolute', left: '10px', top: '50%',
              transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Клиент, ID…"
              style={{ ...iStyle, paddingLeft: '30px', width: '200px' }} />
          </div>

          {/* Shift filter */}
          <button
            onClick={() => setShiftOnly(v => !v)}
            style={{ padding: '5px 12px', borderRadius: '8px', fontSize: '12px', fontWeight: 500,
              cursor: 'pointer', fontFamily: 'inherit', border: '1px solid',
              borderColor: shiftOnly ? '#6366f1' : 'var(--border-color)',
              background: shiftOnly ? 'rgba(99,102,241,0.12)' : 'transparent',
              color: shiftOnly ? '#818cf8' : 'var(--text-muted)',
              display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Clock size={12} />
            {shiftOnly ? 'Текущая смена' : 'Все платежи'}
            {currentShift && shiftOnly && (
              <span style={{ opacity: 0.7, fontSize: '11px' }}>
                ({new Date(currentShift.opened_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })})
              </span>
            )}
          </button>

          {/* Category filter */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {CATEGORIES.map(c => (
              <button key={c.id}
                onClick={() => setFilterCategory(filterCategory === c.id ? '' : c.id)}
                style={{ padding: '5px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 500,
                  cursor: 'pointer', fontFamily: 'inherit', border: 'none',
                  background: filterCategory === c.id ? 'var(--accent)' : 'var(--hover-overlay)',
                  color: filterCategory === c.id ? '#fff' : 'var(--text-muted)' }}>
                {c.label}
              </button>
            ))}
          </div>

          {/* Method filter */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {Object.entries(METHOD).filter(([k]) => k !== 'deposit').map(([k, v]) => (
              <button key={k}
                onClick={() => setFilterMethod(filterMethod === k ? '' : k)}
                style={{ padding: '5px 10px', borderRadius: '8px', fontSize: '11px', fontWeight: 500,
                  cursor: 'pointer', fontFamily: 'inherit', border: 'none',
                  background: filterMethod === k ? v.color + '22' : 'var(--hover-overlay)',
                  color: filterMethod === k ? v.color : 'var(--text-muted)' }}>
                {v.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Payments table */}
      {activeTab === 'payments' && (
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
          borderRadius: '12px', overflow: 'hidden' }}>
          {loading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Загрузка…</div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <Wallet size={32} style={{ opacity: 0.3, marginBottom: '12px', display: 'block', margin: '0 auto 12px' }} />
              Платежей не найдено
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-dark)' }}>
                  {['№', 'Дата / время', 'Клиент', 'Способ', 'Категория', 'Итог', 'Статус', ''].map(col => (
                    <th key={col} style={{ padding: '10px 14px', textAlign: 'left', fontSize: '10px',
                      color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase',
                      letterSpacing: '0.5px', whiteSpace: 'nowrap' }}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => {
                  const method  = METHOD[p.payment_method] || { label: p.payment_method, color: 'var(--text-muted)' };
                  const cat     = getCategory(p);
                  const CatIcon = cat.icon;
                  const refund  = isRefunded(p);
                  return (
                    <tr key={p.id}
                      style={{ borderBottom: '1px solid var(--border-row)', cursor: 'pointer',
                        opacity: refund ? 0.65 : 1, transition: 'background 0.1s' }}
                      onClick={() => setReceiptPayment(p)}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>

                      <td style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>#{p.id}</td>

                      <td style={{ padding: '10px 14px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {fmtDateTime(p.created_at)}
                      </td>

                      <td style={{ padding: '10px 14px', fontWeight: 500 }}>
                        {p.user_username || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Гость</span>}
                      </td>

                      <td style={{ padding: '10px 14px' }}>
                        <span style={{ padding: '2px 8px', borderRadius: '999px', fontSize: '11px',
                          fontWeight: 600, background: method.color + '22', color: method.color }}>
                          {method.label}
                        </span>
                      </td>

                      <td style={{ padding: '10px 14px' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px',
                          padding: '2px 8px', borderRadius: '999px', fontSize: '11px',
                          fontWeight: 600, background: cat.color + '18', color: cat.color }}>
                          <CatIcon size={11} /> {cat.label}
                        </span>
                      </td>

                      <td style={{ padding: '10px 14px', fontWeight: 700, whiteSpace: 'nowrap',
                        color: refund ? '#ef4444' : '#10b981' }}>
                        {refund ? '−' : ''}{fmtMoney(p.amount_paid)}
                        {p.minutes_added > 0 && (
                          <div style={{ fontSize: '10px', color: '#6366f1', fontWeight: 500 }}>
                            +{fmtMins(p.minutes_added)}
                          </div>
                        )}
                      </td>

                      <td style={{ padding: '10px 14px' }}>
                        {refund ? (
                          <span style={{ padding: '2px 8px', borderRadius: '999px', fontSize: '10px',
                            fontWeight: 700, background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}>
                            ВОЗВРАТ
                          </span>
                        ) : (
                          <span style={{ padding: '2px 8px', borderRadius: '999px', fontSize: '10px',
                            fontWeight: 700, background: 'rgba(16,185,129,0.10)', color: '#10b981' }}>
                            АКТИВЕН
                          </span>
                        )}
                      </td>

                      <td style={{ padding: '10px 10px' }} onClick={e => e.stopPropagation()}>
                        {!refund && (
                          <button className="icon-btn"
                            style={{ color: 'var(--danger)', width: '28px', height: '28px' }}
                            title="Отменить платёж" onClick={() => refundPayment(p)}>
                            <RotateCcw size={13} />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Cash orders table */}
      {activeTab === 'cashorders' && (
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
          borderRadius: '12px', overflow: 'hidden' }}>
          {cashOrders.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Кассовых ордеров нет
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-dark)' }}>
                  {['Тип', 'Дата/время', 'Сумма', 'Комментарий'].map(col => (
                    <th key={col} style={{ padding: '10px 14px', textAlign: 'left', fontSize: '10px',
                      color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase',
                      letterSpacing: '0.5px' }}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cashOrders.map(o => (
                  <tr key={o.id}
                    style={{ borderBottom: '1px solid var(--border-row)', transition: 'background 0.1s' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <td style={{ padding: '10px 14px' }}>
                      <span style={{ padding: '2px 8px', borderRadius: '999px', fontSize: '11px', fontWeight: 600,
                        background: o.type === 'pko' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
                        color: o.type === 'pko' ? '#10b981' : '#ef4444' }}>
                        {o.type === 'pko' ? '↓ ПКО' : '↑ РКО'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>{fmtDateTime(o.created_at)}</td>
                    <td style={{ padding: '10px 14px', fontWeight: 700,
                      color: o.type === 'pko' ? '#10b981' : '#ef4444' }}>
                      {o.type === 'pko' ? '+' : '−'}{fmtMoney(o.amount)}
                    </td>
                    <td style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>{o.comment || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ── Modals ── */}
      {receiptPayment && (
        <ReceiptModal
          payment={receiptPayment}
          onClose={() => setReceiptPayment(null)}
          onRefund={(p) => { setReceiptPayment(null); refundPayment(p); }}
        />
      )}

      {orderModal && (
        <div className="modal-overlay" onClick={() => setOrderModal(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px' }}>
            <div className="modal-header">
              <h3>{orderModal === 'pko' ? '↓ ПКО — Внесение' : '↑ РКО — Изъятие'}</h3>
              <button className="icon-btn" onClick={() => setOrderModal(null)}><X size={16} /></button>
            </div>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Сумма сум</label>
                <input type="number" value={orderForm.amount} placeholder="0.00" min="0"
                  onChange={e => setOrderForm(f => ({ ...f, amount: e.target.value }))}
                  style={{ width: '100%', height: '44px', padding: '0 16px',
                    background: 'var(--bg-input)', border: '1px solid var(--border-input)',
                    borderRadius: '8px', color: 'var(--text-main)', fontSize: '18px',
                    fontFamily: 'inherit', fontWeight: 700 }} />
              </div>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Комментарий</label>
                <textarea value={orderForm.comment} placeholder="Причина…" rows={3}
                  onChange={e => setOrderForm(f => ({ ...f, comment: e.target.value }))}
                  style={{ width: '100%', resize: 'vertical' }} />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setOrderModal(null)}>Отмена</button>
              <button className="btn btn-primary"
                style={{ background: orderModal === 'rko' ? '#ef4444' : '' }}
                onClick={createCashOrder}>
                {orderModal === 'pko' ? <><ArrowDownToLine size={14} /> Внести</> : <><ArrowUpFromLine size={14} /> Изъять</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Payments;
