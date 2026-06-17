import { useState, useEffect, useCallback, useRef } from 'react';
import { Box, Check, X, Clock, RefreshCw, Monitor, User } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

const STATUS_CFG = {
  PENDING:    { label: 'Ожидает оплаты', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  PROCESSING: { label: 'Готовится',      color: '#3b82f6', bg: 'rgba(59,130,246,0.12)' },
  COMPLETED:  { label: 'Доставлено',     color: '#10b981', bg: 'rgba(16,185,129,0.12)' },
  CANCELLED:  { label: 'Отменён',        color: '#6b7280', bg: 'rgba(107,114,128,0.12)' },
};
const PAY_METHODS = [
  { id: 'cash', label: 'Наличные' },
  { id: 'card', label: 'Карта' },
  { id: 'transfer', label: 'Перевод' },
  { id: 'deposit', label: 'Депозит' },
];
// Show date + time so orders are unambiguous in the «Все» tab (was HH:MM only).
const fmtTime = (s) => s ? new Date(s).toLocaleString('ru-RU', {
  day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
}) : '';
// Format Decimal amounts as money: thousands separators + «сум» (was raw "15000.00").
const fmtMoney = (v) =>
  v == null || v === '' ? '—' : Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' сум';

const StatusBadge = ({ status }) => {
  const c = STATUS_CFG[status] || STATUS_CFG.PENDING;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 10px',
      borderRadius: 999, fontSize: 11, fontWeight: 600, background: c.bg, color: c.color }}>
      {c.label}
    </span>
  );
};

/* Payment-method picker for confirming a PENDING order */
const PayModal = ({ order, onClose, onPaid }) => {
  const { toast } = useToast();
  const [method, setMethod] = useState('cash');
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      await apiFetch(`/api/v1/shops/orders/admin/${order.id}/pay/`, {
        method: 'POST', body: JSON.stringify({ payment_method: method }),
      });
      toast('Оплата принята, заказ готовится', { type: 'success' });
      onPaid();
    } catch (e) {
      toast(e.body?.error || e.message || 'Ошибка', { type: 'error' }); setBusy(false);
    }
  };
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 3000,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ width: 380, background: 'var(--bg-panel)',
        border: '1px solid var(--border-color)', borderRadius: 14, padding: 22 }}>
        <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>Подтвердить оплату</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
          Заказ #{order.id} · {order.computer_name || '—'} · {order.items_summary}
        </div>
        <div style={{ fontSize: 26, fontWeight: 800, color: '#10b981', marginBottom: 18 }}>
          {fmtMoney(order.total_price)}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>Способ оплаты</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 22 }}>
          {PAY_METHODS.map(m => (
            <button key={m.id} onClick={() => setMethod(m.id)} style={{
              padding: '10px 0', borderRadius: 9, fontSize: 13, fontWeight: 600, cursor: 'pointer',
              border: '1px solid ' + (method === m.id ? '#6366f1' : 'var(--border-color)'),
              background: method === m.id ? 'rgba(99,102,241,0.15)' : 'transparent',
              color: method === m.id ? '#a5b4fc' : 'var(--text-main)',
            }}>{m.label}</button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-secondary" style={{ flex: 1, justifyContent: 'center' }} onClick={onClose} disabled={busy}>Отмена</button>
          <button className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }} onClick={submit} disabled={busy}>
            {busy ? 'Приём…' : `Принять ${fmtMoney(order.total_price)}`}
          </button>
        </div>
      </div>
    </div>
  );
};

const OrderCard = ({ order, onPay, onStatus }) => {
  const c = STATUS_CFG[order.status] || STATUS_CFG.PENDING;
  return (
    <div style={{ background: 'var(--bg-panel)', border: `1px solid ${c.bg}`,
      borderLeft: `3px solid ${c.color}`, borderRadius: 12, padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14 }}>Заказ #{order.id}</div>
          <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 12, color: 'var(--text-muted)' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><Monitor size={12} /> {order.computer_name || '—'}</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><User size={12} /> {order.client?.startsWith('guest-pc-') ? 'Гость' : (order.client || '—')}</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><Clock size={12} /> {fmtTime(order.created_at)}</span>
          </div>
        </div>
        <StatusBadge status={order.status} />
      </div>

      <div style={{ fontSize: 13, marginBottom: 10 }}>
        {(order.items || []).map(it => (
          <div key={it.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
            <span>{it.product_name} × {it.quantity}</span>
            <span style={{ color: 'var(--text-muted)' }}>{fmtMoney(it.subtotal)}</span>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderTop: '1px solid var(--border-color)', paddingTop: 10 }}>
        <div style={{ fontWeight: 700, fontSize: 15 }}>{fmtMoney(order.total_price)}</div>
        <div style={{ display: 'flex', gap: 8 }}>
          {order.status === 'PENDING' && (
            <>
              <button className="btn btn-secondary" style={{ fontSize: 12, borderColor: '#ef4444', color: '#ef4444' }}
                onClick={() => onStatus(order, 'CANCELLED')}><X size={13} /> Отменить</button>
              <button className="btn btn-primary" style={{ fontSize: 12 }} onClick={() => onPay(order)}>
                <Check size={13} /> Подтвердить оплату</button>
            </>
          )}
          {order.status === 'PROCESSING' && (
            <button className="btn btn-primary" style={{ fontSize: 12, background: '#10b981', borderColor: '#10b981' }}
              onClick={() => onStatus(order, 'COMPLETED')}><Check size={13} /> Доставлено</button>
          )}
        </div>
      </div>
    </div>
  );
};

const Orders = () => {
  const { toast } = useToast();
  const clubId = localStorage.getItem('active_club_id');
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [payOrder, setPayOrder] = useState(null);
  const [filter, setFilter] = useState('active'); // active | all
  const timer = useRef(null);

  const load = useCallback(async () => {
    if (!clubId) { setLoading(false); return; }
    try {
      const data = await apiFetch(`/api/v1/shops/orders/admin/?club=${clubId}`);
      setOrders(Array.isArray(data) ? data : (data.results || []));
    } catch { /* keep previous */ }
    finally { setLoading(false); }
  }, [clubId]);

  // Initial load + light polling so new orders appear without a manual refresh.
  useEffect(() => {
    load();
    timer.current = setInterval(load, 10000);
    return () => clearInterval(timer.current);
  }, [load]);

  const changeStatus = async (order, status) => {
    if (status === 'CANCELLED' && !window.confirm(`Отменить заказ #${order.id}?`)) return;
    try {
      await apiFetch(`/api/v1/shops/orders/admin/${order.id}/status/`, {
        method: 'POST', body: JSON.stringify({ status }),
      });
      toast(status === 'COMPLETED' ? 'Заказ доставлен' : 'Заказ отменён', { type: 'success' });
      load();
    } catch (e) { toast(e.body?.error || e.message || 'Ошибка', { type: 'error' }); }
  };

  const active = orders.filter(o => o.status === 'PENDING' || o.status === 'PROCESSING');
  const shown = filter === 'active' ? active : orders;
  const newCount = orders.filter(o => o.status === 'PENDING').length;

  return (
    <div style={{ padding: '20px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Box size={22} />
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Заказы</h1>
            {newCount > 0 && (
              <span style={{ background: '#f59e0b', color: '#000', fontSize: 12, fontWeight: 700,
                padding: '2px 9px', borderRadius: 999 }}>{newCount} новых</span>
            )}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
            Заказы из шелла. Подтвердите оплату и отметьте доставку.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {['active', 'all'].map(f => (
            <button key={f} onClick={() => setFilter(f)} className="btn btn-secondary"
              style={{ fontSize: 12, ...(filter === f ? { borderColor: '#6366f1', color: '#a5b4fc' } : {}) }}>
              {f === 'active' ? 'Активные' : 'Все'}
            </button>
          ))}
          <button className="btn btn-secondary" style={{ fontSize: 12 }} onClick={load}><RefreshCw size={13} /> Обновить</button>
        </div>
      </div>

      {loading ? (
        <div style={{ color: 'var(--text-muted)', padding: 40, textAlign: 'center' }}>Загрузка…</div>
      ) : shown.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', padding: 60, textAlign: 'center' }}>
          <Box size={40} style={{ opacity: 0.4 }} />
          <div style={{ marginTop: 12 }}>{filter === 'active' ? 'Активных заказов нет' : 'Заказов пока нет'}</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 14 }}>
          {shown.map(o => (
            <OrderCard key={o.id} order={o} onPay={setPayOrder} onStatus={changeStatus} />
          ))}
        </div>
      )}

      {payOrder && (
        <PayModal order={payOrder} onClose={() => setPayOrder(null)}
          onPaid={() => { setPayOrder(null); load(); }} />
      )}
    </div>
  );
};

export default Orders;
