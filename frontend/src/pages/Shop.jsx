import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search, Plus, Minus, Trash2,
  X, ChevronDown,
  Package, RefreshCw, Archive,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

/* ─── helpers ─────────────────────────────────────────────────────────── */
const fmtMoney = (v) =>
  Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' сум';

const fmtQty = (v) =>
  v == null ? '∞' : Number(v).toLocaleString('ru-RU') + ' шт.';

/* Extract the REAL backend reason from an apiFetch error. apiFetch throws
 * `new Error('HTTP <status>')` but attaches the parsed response body as `err.body`
 * (e.g. { message } / { error } / { detail } / DRF field errors). Without this the
 * operator only ever saw "HTTP 400" instead of e.g. «Недостаточно «Cola»: 3 шт.». */
const errMsg = (e) => {
  const b = e && e.body;
  if (b) {
    if (typeof b === 'string' && b.trim()) return b;
    if (typeof b === 'object') {
      if (b.message) return b.message;
      if (b.error) return b.error;
      if (b.detail) return b.detail;
      // DRF field/non_field errors → first string we can find.
      for (const v of Object.values(b)) {
        if (typeof v === 'string') return v;
        if (Array.isArray(v) && v.length && typeof v[0] === 'string') return v[0];
      }
    }
  }
  return (e && e.message) || 'Ошибка сервера';
};

/* ─── Stock entry modal (Оприходование товара) ───────────────────────── */
const StockEntryModal = ({ products, onClose, onDone }) => {
  const { toast } = useToast();
  const [rows, setRows] = useState([{ id: Date.now(), productId: '', qty: 1, comment: 'Новая поставка' }]);
  const [saving, setSaving] = useState(false);

  const addRow = () => setRows(r => [...r, { id: Date.now(), productId: '', qty: 1, comment: 'Новая поставка' }]);
  const delRow = (id) => setRows(r => r.filter(x => x.id !== id));
  const setRow = (id, field, val) => setRows(r => r.map(x => x.id === id ? { ...x, [field]: val } : x));

  const submit = async () => {
    const valid = rows.filter(r => r.productId && r.qty > 0);
    if (!valid.length) { toast('Добавьте хотя бы один товар', { type: 'warning' }); return; }
    setSaving(true);
    // BUGFIX: Promise.all rejected on the FIRST failed row, but the rows that
    // already succeeded had stock applied server-side — leaving partial state and
    // never refreshing (onDone skipped). Use allSettled so we always report how
    // many landed, surface the real per-row error, and refresh regardless.
    const results = await Promise.allSettled(valid.map(r =>
      apiFetch(`/api/v1/shops/admin/products/${r.productId}/stock/`, {
        method: 'POST',
        body: JSON.stringify({ delta: Number(r.qty), reason: r.comment || 'Поставка' }),
      })
    ));
    setSaving(false);
    const ok = results.filter(x => x.status === 'fulfilled').length;
    const failed = results.length - ok;
    if (failed > 0) {
      const firstErr = results.find(x => x.status === 'rejected')?.reason;
      toast(`Внесено: ${ok}, не удалось: ${failed}. ${errMsg(firstErr)}`,
        { type: ok > 0 ? 'warning' : 'error' });
      // Even on partial failure some stock changed — refresh so the catalog is accurate.
      onDone();
      return;
    }
    toast(`Внесено: ${ok} позиций`, { type: 'success' });
    onDone();
  };

  return (
    <div onClick={e => e.target === e.currentTarget && onClose()}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 14, width: 560,
        maxHeight: '85vh', border: '1px solid var(--border-color)',
        display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border-color)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
          <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>Оприходование товара</h3>
          <button className="icon-btn" onClick={onClose}><X size={15} /></button>
        </div>

        {/* Add from list */}
        <div style={{ padding: '14px 22px', borderBottom: '1px solid var(--border-color)', flexShrink: 0 }}>
          <div style={{ position: 'relative' }}>
            <select onChange={e => {
                if (e.target.value) { setRows(r => [...r, { id: Date.now(), productId: e.target.value, qty: 1, comment: 'Новая поставка' }]); e.target.value = ''; }
              }}
              style={{ height: 40, width: '100%', padding: '0 32px 0 12px',
                background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                borderRadius: 8, color: 'var(--text-muted)', fontSize: '13px', fontFamily: 'inherit',
                appearance: 'none', cursor: 'pointer' }}>
              <option value="">Добавить товар из списка</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <ChevronDown size={14} style={{ position: 'absolute', right: 10, top: '50%',
              transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
          </div>
        </div>

        {/* Rows */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '10px 22px' }}>
          {rows.map((row) => (
            <div key={row.id} style={{ marginBottom: 14, padding: 14,
              background: 'var(--bg-dark)', borderRadius: 10,
              border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', gap: 10, marginBottom: 8 }}>
                {/* Product select */}
                <div style={{ flex: 1, position: 'relative' }}>
                  <select value={row.productId} onChange={e => setRow(row.id, 'productId', e.target.value)}
                    style={{ height: 38, width: '100%', padding: '0 28px 0 10px',
                      background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
                      borderRadius: 8, color: row.productId ? 'var(--text-main)' : 'var(--text-muted)',
                      fontSize: '13px', fontFamily: 'inherit', appearance: 'none' }}>
                    <option value="">— товар —</option>
                    {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <ChevronDown size={12} style={{ position: 'absolute', right: 8, top: '50%',
                    transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
                </div>
                {/* Qty */}
                <div style={{ width: 90 }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: 3 }}>Количество</div>
                  <input type="number" min={1} value={row.qty}
                    onChange={e => setRow(row.id, 'qty', Math.max(1, parseInt(e.target.value) || 1))}
                    style={{ height: 38, width: '100%', padding: '0 10px', boxSizing: 'border-box',
                      background: 'var(--bg-panel)', border: '1px solid var(--accent)',
                      borderRadius: 8, color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit' }} />
                </div>
                {/* Delete */}
                <button onClick={() => delRow(row.id)}
                  style={{ width: 38, height: 38, flexShrink: 0, borderRadius: 8,
                    background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
                    cursor: 'pointer', color: '#ef4444', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    alignSelf: 'flex-end' }}>
                  <Trash2 size={14} />
                </button>
              </div>
              {/* Comment */}
              <div style={{ position: 'relative' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: 3 }}>
                  Комментарий
                  <span style={{ float: 'right' }}>{row.comment.length}/255</span>
                </div>
                <input value={row.comment}
                  onChange={e => setRow(row.id, 'comment', e.target.value.slice(0, 255))}
                  style={{ height: 34, width: '100%', padding: '0 10px', boxSizing: 'border-box',
                    background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
                    borderRadius: 8, color: 'var(--text-main)', fontSize: '12px', fontFamily: 'inherit' }} />
              </div>
            </div>
          ))}
          <button onClick={addRow} style={{ width: '100%', height: 36, border: '1px dashed var(--border-color)',
            borderRadius: 8, background: 'none', color: 'var(--text-muted)', fontSize: '13px',
            cursor: 'pointer', fontFamily: 'inherit', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <Plus size={13} /> Добавить строку
          </button>
        </div>

        {/* Footer */}
        <div style={{ padding: '14px 22px', borderTop: '1px solid var(--border-color)', flexShrink: 0 }}>
          <button className="btn btn-primary" style={{ width: '100%', height: 44, justifyContent: 'center' }}
            onClick={submit} disabled={saving}>
            {saving ? 'Внесение…' : 'Внести'}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Left panel: client search + discounts + promo ──────────────────── */
const LeftPanel = ({ client, onSelectClient, onClearClient, discounts, promoApplied, onApplyPromo }) => {
  const { toast } = useToast();
  const [query, setQuery]     = useState('');
  const [results, setResults] = useState([]);
  const [open, setOpen]       = useState(false);
  const [promoCode, setPromoCode] = useState('');
  const [sortDisc, setSortDisc]   = useState({ col: 'name', dir: 1 });
  const timer = useRef();
  const clubId = localStorage.getItem('active_club_id');
  const searchRef = useRef();

  /* close dropdown on outside click */
  useEffect(() => {
    const h = (e) => { if (searchRef.current && !searchRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  const handleInput = (e) => {
    const q = e.target.value;
    setQuery(q);
    clearTimeout(timer.current);
    if (!q.trim()) { setResults([]); setOpen(false); return; }
    timer.current = setTimeout(async () => {
      try {
        const r = await apiFetch(`/api/v1/billing/admin/users/?search=${encodeURIComponent(q)}&club=${clubId}`);
        setResults((r.results || r || []).slice(0, 6));
        setOpen(true);
      } catch { setResults([]); }
    }, 280);
  };

  const applyPromo = async () => {
    const code = promoCode.trim();
    if (!code) return;
    try {
      const r = await apiFetch(`/api/v1/loyalty/promocodes/?code=${encodeURIComponent(code)}&club=${clubId}`);
      const list = r.results || r || [];
      const p = list.find(x => x.code === code && x.is_active !== false);
      if (p) { onApplyPromo(p); toast(`Промокод «${code}» применён`, { type: 'success' }); }
      else toast('Промокод не найден', { type: 'error' });
    } catch { onApplyPromo({ code }); toast('Промокод будет проверен при оплате', { type: 'info' }); }
  };

  const sortedDisc = [...discounts].sort((a, b) => {
    const av = sortDisc.col === 'name' ? (a.name || '') : Number(a.value || 0);
    const bv = sortDisc.col === 'name' ? (b.name || '') : Number(b.value || 0);
    return typeof av === 'string' ? av.localeCompare(bv) * sortDisc.dir : (av - bv) * sortDisc.dir;
  });

  const toggleSort = (col) => setSortDisc(s => ({ col, dir: s.col === col ? -s.dir : 1 }));
  const SortIcon = ({ col }) => {
    if (sortDisc.col !== col) return <span style={{ opacity: 0.3 }}>↕</span>;
    return <span style={{ color: 'var(--accent)' }}>{sortDisc.dir === 1 ? '↑' : '↓'}</span>;
  };

  const iStyle = {
    height: 36, padding: '0 10px', width: '100%', boxSizing: 'border-box',
    background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
    borderRadius: 8, color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit',
  };

  return (
    <div style={{ width: 268, flexShrink: 0, borderRight: '1px solid var(--border-color)',
      display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

      {/* Client search */}
      <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-color)', flexShrink: 0 }}>
        {!client ? (
          <div ref={searchRef} style={{ position: 'relative' }}>
            <div style={{ position: 'relative' }}>
              <Search size={13} style={{ position: 'absolute', left: 10, top: '50%',
                transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
              <input value={query} onChange={handleInput}
                placeholder="Найти клиента"
                style={{ ...iStyle, paddingLeft: 30 }} />
            </div>
            {open && results.length > 0 && (
              <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 4,
                background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
                borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.3)', zIndex: 100, overflow: 'hidden' }}>
                {results.map(u => (
                  <div key={u.id} onClick={() => { onSelectClient(u); setQuery(''); setOpen(false); }}
                    style={{ padding: '9px 12px', cursor: 'pointer', borderBottom: '1px solid var(--border-row)' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>{u.username}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{u.phone || u.email || '—'}</div>
                  </div>
                ))}
              </div>
            )}
            <div style={{ marginTop: 8, fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
              Начните вводить никнейм или телефон авторизованного клиента.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 0' }}>
            <div style={{ width: 36, height: 36, borderRadius: '50%',
              background: 'rgba(99,102,241,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '15px', fontWeight: 700, color: 'var(--accent)', flexShrink: 0 }}>
              {(client.username || 'U')[0].toUpperCase()}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {client.username}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {client.phone || client.email || '—'}
              </div>
            </div>
            <button className="icon-btn" style={{ width: 22, height: 22 }} onClick={onClearClient}>
              <X size={13} />
            </button>
          </div>
        )}

        {/* Client stats */}
        {client && (
          <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
            {[
              { label: 'Депозит', value: fmtMoney(client.deposit_money || client.balance || 0), color: '#10b981' },
              { label: 'Бонусы',  value: fmtMoney(client.bonus_balance || 0), color: '#f59e0b' },
              // Show effective (max of personal/group) discount — the one actually applied at checkout.
              { label: 'Скидка',  value: `${client.effective_discount ?? client.personal_discount ?? 0}%`, color: '#8b5cf6' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ flex: 1, textAlign: 'center', padding: '6px 4px',
                background: 'var(--hover-overlay)', borderRadius: 8 }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color }}>{value}</div>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>{label}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Discounts table */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0' }}>
        {discounts.length > 0 && (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-dark)' }}>
                <th onClick={() => toggleSort('name')}
                  style={{ padding: '7px 12px', textAlign: 'left', cursor: 'pointer',
                    fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600,
                    textTransform: 'uppercase', letterSpacing: '0.5px', userSelect: 'none' }}>
                  Название <SortIcon col="name" />
                </th>
                <th onClick={() => toggleSort('value')}
                  style={{ padding: '7px 12px', textAlign: 'right', cursor: 'pointer',
                    fontSize: '10px', color: 'var(--text-muted)', fontWeight: 600,
                    textTransform: 'uppercase', letterSpacing: '0.5px', userSelect: 'none', whiteSpace: 'nowrap' }}>
                  Скид... <SortIcon col="value" />
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedDisc.map(d => (
                <tr key={d.id} style={{ borderBottom: '1px solid var(--border-row)', cursor: 'pointer' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td style={{ padding: '8px 12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    maxWidth: 140 }}>{d.name}</td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 600, color: '#10b981' }}>
                    {d.value}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Promo code */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border-color)', flexShrink: 0 }}>
        {promoApplied ? (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '6px 10px', background: 'rgba(16,185,129,0.08)',
            border: '1px solid rgba(16,185,129,0.25)', borderRadius: 6 }}>
            <span style={{ fontSize: '12px', color: '#10b981', fontWeight: 600 }}>
              ✓ {promoApplied.code}{promoApplied.value ? ` −${promoApplied.value}%` : ''}
            </span>
            <button onClick={() => onApplyPromo(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: '15px', lineHeight: 1 }}>×</button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 6 }}>
            <input value={promoCode} onChange={e => setPromoCode(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && applyPromo()}
              placeholder="Введите промокод"
              style={{ ...iStyle, flex: 1 }} />
            <button className="btn btn-secondary" onClick={applyPromo}
              style={{ padding: '0 12px', fontSize: '12px', whiteSpace: 'nowrap' }}>
              Применить
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

/* ─── Right cart panel ────────────────────────────────────────────────── */
const CartPanel = ({ items, discount, promoApplied, onQty, onRemove, onCheckout, busy }) => {
  const [method, setMethod] = useState('cash');
  // Split (cash/card) part — only the cash side is edited; card is the remainder.
  const [cashPart, setCashPart] = useState('');

  const subtotal = items.reduce((s, i) => s + i.price * i.qty, 0);
  const discPct  = discount || (promoApplied?.reward_type === 'discount' ? Number(promoApplied.value) : 0);
  // NOTE: backend only discounts lines whose item has applies_discount=true (see
  // shops/api/v1/views/sell.py). It does NOT discount non-discountable items, so on a
  // mixed cart this displayed total can read slightly LOWER than what's actually
  // charged. We intentionally do NOT replicate that per-item rule here: the catalog
  // payload (ProductAdminSerializer) does not expose `applies_discount`, so guessing
  // it client-side would risk being even more wrong. Backend total is authoritative.
  const discAmt  = Math.round(subtotal * discPct / 100);
  const total    = Math.max(0, subtotal - discAmt);

  // For the split method: cash = entered (clamped to [0,total]); card = the rest.
  const cashNum  = Math.min(Math.max(parseInt(cashPart, 10) || 0, 0), total);
  const cardNum  = Math.max(0, total - cashNum);

  const METHODS = [
    { id: 'cash',    label: 'Наличные' },
    { id: 'card',    label: 'Карта' },
    { id: 'balance', label: 'Депозит' },
    { id: 'split',   label: 'Разделить' },
  ];

  const handlePay = () => {
    if (busy || items.length === 0) return;
    // BUGFIX: «Разделить» used to send method:'split' with no parts, so the backend
    // (which only knows cash/card/balance/composite) fell through to CASH and the
    // whole sale was recorded as cash. Send the documented 'composite' method with
    // cash_part/card_part so the operator's chosen split is actually submitted.
    if (method === 'split') {
      onCheckout('composite', { cash_part: cashNum, card_part: cardNum });
    } else {
      onCheckout(method);
    }
  };

  return (
    <div style={{ width: 240, flexShrink: 0, borderLeft: '1px solid var(--border-color)',
      display: 'flex', flexDirection: 'column' }}>

      {/* Cart items */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 14px' }}>
        {items.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)', fontSize: '12px' }}>
            <Package size={26} style={{ opacity: 0.25, marginBottom: 8 }} />
            <div>Корзина пуста</div>
          </div>
        ) : items.map(item => (
          <div key={item.cartId} style={{ marginBottom: 12, borderBottom: '1px solid var(--border-row)', paddingBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
              <div style={{ fontSize: '13px', fontWeight: 600, flex: 1, paddingRight: 8,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {item.name}
              </div>
              <button onClick={() => onRemove(item.cartId)}
                style={{ background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--text-muted)', padding: 0, lineHeight: 1 }}>
                <Trash2 size={13} />
              </button>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button onClick={() => onQty(item.cartId, -1)}
                  style={{ width: 22, height: 22, borderRadius: 4, border: '1px solid var(--border-color)',
                    background: 'var(--bg-dark)', cursor: 'pointer', color: 'var(--text-main)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Minus size={11} />
                </button>
                <span style={{ fontSize: '14px', fontWeight: 700, minWidth: 20, textAlign: 'center' }}>
                  {item.qty}
                </span>
                <button onClick={() => onQty(item.cartId, 1)}
                  style={{ width: 22, height: 22, borderRadius: 4, border: '1px solid var(--border-color)',
                    background: 'var(--bg-dark)', cursor: 'pointer', color: 'var(--text-main)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Plus size={11} />
                </button>
              </div>
              <span style={{ fontSize: '13px', fontWeight: 700 }}>
                {fmtMoney(item.price * item.qty)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={{ padding: '12px 14px', borderTop: '1px solid var(--border-color)', flexShrink: 0 }}>
        {/* Discount row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: 10, fontSize: '12px' }}>
          <span style={{ color: 'var(--text-muted)' }}>Скидка</span>
          <span style={{ color: discAmt > 0 ? '#10b981' : 'var(--text-muted)', fontWeight: discAmt > 0 ? 600 : 400 }}>
            {discAmt > 0 ? `−${fmtMoney(discAmt)}` : '—'}
          </span>
        </div>

        {/* Payment methods */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 5, marginBottom: 10 }}>
          {METHODS.map(m => (
            <button key={m.id} onClick={() => setMethod(m.id)}
              style={{ height: 42, border: `1px solid ${method === m.id ? 'var(--accent)' : 'var(--border-color)'}`,
                borderRadius: 8, background: method === m.id ? 'rgba(99,102,241,0.12)' : 'var(--bg-dark)',
                color: method === m.id ? 'var(--accent)' : 'var(--text-muted)',
                fontSize: '11px', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>
              {m.label}
            </button>
          ))}
        </div>

        {/* Split amounts — only for «Разделить». Cash is entered, card is the rest. */}
        {method === 'split' && (
          <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: 3 }}>Наличные</div>
              <input type="number" min={0} max={total} value={cashPart}
                onChange={e => setCashPart(e.target.value)}
                placeholder="0"
                style={{ height: 34, width: '100%', padding: '0 8px', boxSizing: 'border-box',
                  background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                  borderRadius: 8, color: 'var(--text-main)', fontSize: '12px', fontFamily: 'inherit' }} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: 3 }}>Карта</div>
              <div style={{ height: 34, display: 'flex', alignItems: 'center', padding: '0 8px',
                background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                borderRadius: 8, color: 'var(--text-main)', fontSize: '12px' }}>
                {fmtMoney(cardNum)}
              </div>
            </div>
          </div>
        )}

        {/* Pay button */}
        <button className="btn btn-primary"
          style={{ width: '100%', height: 42, justifyContent: 'center', fontSize: '13px',
            opacity: (items.length === 0 || busy) ? 0.4 : 1,
            cursor: (items.length === 0 || busy) ? 'not-allowed' : 'pointer' }}
          // BUGFIX: button was only disabled on empty cart, so a fast double-click
          // fired two checkouts (duplicate order). The parent also swapped onCheckout
          // for `undefined` while busy, which made the 2nd click throw a TypeError.
          // Disable on `busy` here and guard inside handlePay → at most one request.
          disabled={items.length === 0 || busy}
          onClick={handlePay}>
          {busy ? 'Оплата…' : `Оплатить ${items.length > 0 ? fmtMoney(total) : ''}`}
        </button>
      </div>
    </div>
  );
};

/* ─── Main Shop ───────────────────────────────────────────────────────── */
const Shop = () => {
  const { toast } = useToast();
  const clubId = localStorage.getItem('active_club_id');

  const [client, setClient]   = useState(null);
  const [products, setProducts] = useState([]);
  const [services, setServices] = useState([]);
  const [combos, setCombos]   = useState([]);
  const [discounts, setDiscounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab]         = useState('products');
  const [search, setSearch]   = useState('');
  const [cart, setCart]       = useState([]);
  const [promoApplied, setPromoApplied] = useState(null);
  const [stockModal, setStockModal] = useState(false);
  const [checking, setChecking] = useState(false);
  const [sortCatalog, setSortCatalog] = useState({ col: 'name', dir: 1 });

  /* ── load ── */
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [prods, servs, combs, discs] = await Promise.all([
        // limit=500: DRF LimitOffsetPagination caps at 20 by default, which made
        // products/services/combos #21+ unsellable in POS and hid discounts past #20.
        apiFetch(`/api/v1/shops/admin/products/?club=${clubId || ''}&limit=500`).catch(() => []),
        apiFetch(`/api/v1/shops/services/?club=${clubId || ''}&limit=500`).catch(() => []),
        apiFetch(`/api/v1/shops/combos/?club=${clubId || ''}&limit=500`).catch(() => []),
        apiFetch(`/api/v1/loyalty/discounts/?club=${clubId || ''}&limit=500`).catch(() => []),
      ]);
      setProducts(prods.results || prods || []);
      setServices(servs.results || servs || []);
      setCombos(combs.results || combs || []);
      setDiscounts(discs.results || discs || []);
    } finally { setLoading(false); }
  }, [clubId]);

  useEffect(() => { load(); }, [load]);

  /* ── catalog ── */
  const rawItems = tab === 'products' ? products : tab === 'services' ? services : combos;
  const catalogItems = rawItems
    .filter(i => !search || (i.name || '').toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      let av = sortCatalog.col === 'name'  ? (a.name || '')
             : sortCatalog.col === 'group' ? (a.category?.name || a.group_name || '')
             : sortCatalog.col === 'qty'   ? Number(a.current_stock || 0)
             : Number(a.price || a.sale_price || 0);
      let bv = sortCatalog.col === 'name'  ? (b.name || '')
             : sortCatalog.col === 'group' ? (b.category?.name || b.group_name || '')
             : sortCatalog.col === 'qty'   ? Number(b.current_stock || 0)
             : Number(b.price || b.sale_price || 0);
      return typeof av === 'string' ? av.localeCompare(bv) * sortCatalog.dir : (av - bv) * sortCatalog.dir;
    });

  const toggleSort = (col) => setSortCatalog(s => ({ col, dir: s.col === col ? -s.dir : 1 }));
  const SortArrow = ({ col }) => {
    if (sortCatalog.col !== col) return <span style={{ opacity: 0.3 }}>↕</span>;
    return <span style={{ color: 'var(--accent)' }}>{sortCatalog.dir === 1 ? '↑' : '↓'}</span>;
  };

  /* ── cart ops ── */
  // Products carry current_stock; services/combos don't (treated as unlimited). Cap cart
  // quantity at the stock — the backend rejects oversell with 400, so without this the
  // operator could build a cart of 30 from 9 in stock and only fail at payment.
  const stockOf = (it) => (it?.current_stock == null ? Infinity : Number(it.current_stock));

  const addToCart = (item) => {
    const max = stockOf(item);
    setCart(prev => {
      const price = Number(item.price ?? item.sale_price ?? item.base_price ?? 0);
      const ex = prev.find(c => c.id === item.id && c.type === tab);
      if ((ex ? ex.qty : 0) + 1 > max) {
        toast(`Недостаточно на складе: всего ${max} шт.`, { type: 'warning' });
        return prev;
      }
      if (ex) return prev.map(c => c.id === item.id && c.type === tab ? { ...c, qty: c.qty + 1 } : c);
      return [...prev, { ...item, price, qty: 1, type: tab, cartId: `${tab}_${item.id}` }];
    });
  };
  const updateQty = (cartId, delta) => setCart(prev =>
    prev.map(c => {
      if (c.cartId !== cartId) return c;
      if (delta > 0 && c.qty + delta > stockOf(c)) {
        toast(`Недостаточно на складе: всего ${stockOf(c)} шт.`, { type: 'warning' });
        return c;
      }
      return { ...c, qty: c.qty + delta };
    }).filter(c => c.qty > 0));
  const removeItem = (cartId) => setCart(prev => prev.filter(c => c.cartId !== cartId));

  /* ── checkout ── */
  const checkout = async (payMethod, extra = {}) => {
    if (cart.length === 0 || checking) return;
    setChecking(true);

    // BUGFIX: was client.personal_discount, which ignored the group discount.
    // effective_discount = max(personal, group) — matches the backend rule and is
    // returned on the client object by /billing/admin/users/. Fall back to
    // personal_discount for older payloads that lack effective_discount.
    const discPct = Number(client?.effective_discount ?? client?.personal_discount ?? 0) ||
                    (promoApplied?.reward_type === 'discount' ? Number(promoApplied.value) : 0);

    try {
      await apiFetch('/api/v1/shops/sell/', {
        method: 'POST',
        body: JSON.stringify({
          client_id: client?.id || null,
          payment_method: payMethod,
          items: cart.map(c => ({ kind: c.type, id: c.id, qty: c.qty })),
          club: clubId,
          discount_percent: discPct,   // ← передаём скидку бэкенду
          ...(promoApplied?.code ? { promocode_code: promoApplied.code } : {}),
          ...extra,                    // cash_part/card_part for split (composite)
        }),
      });
      toast('Оплачено успешно', { type: 'success' });
      setCart([]);
      setPromoApplied(null);
      load(); // refresh stock quantities
    } catch (e) {
      // BUGFIX: was `e.message` → always the generic "HTTP 400". Surface the real
      // backend reason (cart empty / not enough stock / insufficient deposit, …).
      toast('Ошибка оплаты: ' + errMsg(e), { type: 'error' });
    } finally { setChecking(false); }
  };

  const TABS = [
    { id: 'products', label: 'Товары' },
    { id: 'services', label: 'Услуги' },
    { id: 'combos',   label: 'Комбо-наборы' },
  ];

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── LEFT ── */}
      <LeftPanel
        client={client}
        onSelectClient={(u) => { setClient(u); setPromoApplied(null); }}
        onClearClient={() => { setClient(null); setPromoApplied(null); }}
        discounts={discounts}
        promoApplied={promoApplied}
        onApplyPromo={setPromoApplied}
      />

      {/* ── CENTER ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Center header */}
        <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border-color)',
          display: 'flex', gap: 8, alignItems: 'center', flexShrink: 0 }}>
          {/* Tabs */}
          <div style={{ display: 'flex', gap: 3 }}>
            {TABS.map(t => (
              <button key={t.id} onClick={() => { setTab(t.id); setSearch(''); }}
                style={{ padding: '6px 14px', borderRadius: 8, fontSize: '13px', fontWeight: 500,
                  cursor: 'pointer', fontFamily: 'inherit', border: 'none',
                  background: tab === t.id ? 'var(--accent)' : 'var(--hover-overlay)',
                  color: tab === t.id ? '#fff' : 'var(--text-muted)' }}>
                {t.label}
              </button>
            ))}
          </div>
          <div style={{ flex: 1 }} />
          {/* Search */}
          <div style={{ position: 'relative' }}>
            <Search size={12} style={{ position: 'absolute', left: 9, top: '50%',
              transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Поиск"
              style={{ paddingLeft: 28, paddingRight: 10, height: 34, width: 170,
                background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                borderRadius: 8, color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit' }} />
          </div>
          <button className="icon-btn" onClick={load} disabled={loading}><RefreshCw size={14} /></button>
        </div>

        {/* Stock entry button (top-right area, outside the catalog header) */}
        <div style={{ padding: '10px 16px', display: 'flex', justifyContent: 'flex-end',
          borderBottom: '1px solid var(--border-color)', flexShrink: 0 }}>
          <button className="btn btn-secondary" onClick={() => setStockModal(true)}
            style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '12px' }}>
            <Archive size={13} /> Внесение на склад
          </button>
        </div>

        {/* Catalog table */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
              Загрузка каталога…
            </div>
          ) : catalogItems.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)',
              background: 'var(--bg-panel)', borderRadius: 12, border: '1px solid var(--border-color)' }}>
              <Package size={32} style={{ opacity: 0.3, marginBottom: 12 }} />
              <div>Нет позиций</div>
            </div>
          ) : (
            <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
              borderRadius: 12, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-dark)' }}>
                    {[
                      { id: 'name',  label: 'Название' },
                      { id: 'group', label: 'Группа' },
                      { id: 'qty',   label: 'Количество' },
                      { id: 'price', label: 'Стоимость' },
                    ].map(c => (
                      <th key={c.id} onClick={() => toggleSort(c.id)}
                        style={{ padding: '10px 14px', textAlign: 'left', fontSize: '10px',
                          color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase',
                          letterSpacing: '0.5px', cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' }}>
                        {c.label} <SortArrow col={c.id} />
                      </th>
                    ))}
                    <th style={{ width: 40 }} />
                  </tr>
                </thead>
                <tbody>
                  {catalogItems.map(item => {
                    const inCart = cart.find(c => c.id === item.id && c.type === tab);
                    const groupName = item.category?.name || item.group_name || null;
                    return (
                      <tr key={item.id} onClick={() => addToCart(item)}
                        style={{ borderBottom: '1px solid var(--border-row)', cursor: 'pointer',
                          background: inCart ? 'rgba(99,102,241,0.04)' : 'transparent' }}
                        onMouseEnter={e => { if (!inCart) e.currentTarget.style.background = 'var(--hover-overlay)'; }}
                        onMouseLeave={e => { if (!inCart) e.currentTarget.style.background = 'transparent'; }}>
                        <td style={{ padding: '10px 14px', fontWeight: 600 }}>
                          {item.name}
                          {inCart && (
                            <span style={{ marginLeft: 8, background: 'rgba(99,102,241,0.15)',
                              color: 'var(--accent)', borderRadius: '999px', fontSize: '10px',
                              padding: '1px 6px', fontWeight: 700 }}>×{inCart.qty}</span>
                          )}
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          {groupName ? (
                            <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '999px',
                              background: 'rgba(99,102,241,0.1)', color: 'var(--accent)', fontWeight: 500 }}>
                              {groupName}
                            </span>
                          ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                        </td>
                        <td style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>
                          {fmtQty(item.current_stock)}
                        </td>
                        <td style={{ padding: '10px 14px', fontWeight: 700 }}>
                          {fmtMoney(item.price || item.sale_price || item.base_price)}
                        </td>
                        <td style={{ padding: '10px 10px' }}>
                          <button onClick={e => { e.stopPropagation(); addToCart(item); }}
                            style={{ width: 28, height: 28, borderRadius: 8, border: 'none',
                              background: 'rgba(99,102,241,0.12)', color: 'var(--accent)',
                              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Plus size={13} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* ── RIGHT CART ── */}
      <CartPanel
        items={cart}
        // effective_discount = max(personal, group); falls back to personal for old payloads.
        discount={client?.effective_discount ?? client?.personal_discount ?? 0}
        promoApplied={promoApplied}
        onQty={updateQty}
        onRemove={removeItem}
        // Pass a STABLE callback + a `busy` flag instead of swapping onCheckout for
        // undefined while checking (which made a 2nd click call undefined() → TypeError).
        onCheckout={checkout}
        busy={checking}
      />

      {/* ── Stock entry modal ── */}
      {stockModal && (
        <StockEntryModal
          products={products}
          onClose={() => setStockModal(false)}
          onDone={() => { setStockModal(false); load(); }}
        />
      )}
    </div>
  );
};

export default Shop;
