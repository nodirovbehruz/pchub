import { useState, useEffect, useCallback } from 'react';
import { Crown, Wallet, Check, Clock, AlertCircle, RefreshCw } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

const fmtMoney = (v) => Number(v || 0).toLocaleString('ru-RU') + ' сум';
const fmtDate = (s) => s ? new Date(s).toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' }) : '—';
const daysLeft = (s) => s ? Math.ceil((new Date(s) - Date.now()) / 86400000) : null;

const STATUS = {
  active:   { label: 'Активна',          color: '#10b981' },
  trial:    { label: 'Пробный период',   color: '#3b82f6' },
  promised: { label: 'Обещанный платёж', color: '#f59e0b' },
  expired:  { label: 'Истекла',          color: '#ef4444' },
  blocked:  { label: 'Заблокирована',    color: '#ef4444' },
};

const Subscription = () => {
  const { toast } = useToast();
  const clubId = localStorage.getItem('active_club_id');
  const [wallet, setWallet] = useState({ balance: '0', transactions: [] });
  const [sub, setSub] = useState(null);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    if (!clubId) { setLoading(false); return; }
    try {
      const [w, s, p] = await Promise.all([
        apiFetch(`/api/v1/clubs/${clubId}/wallet/`).catch(() => ({ balance: '0', transactions: [] })),
        apiFetch(`/api/v1/clubs/${clubId}/subscription/`).catch(() => null),
        apiFetch(`/api/v1/clubs/plans/`).catch(() => []),
      ]);
      setWallet({
        balance: w?.balance ?? '0',
        pc_usage: w?.pc_usage,
        transactions: Array.isArray(w?.transactions) ? w.transactions : [],
      });
      setSub(s);
      setPlans(Array.isArray(p) ? p : []);
    } finally { setLoading(false); }
  }, [clubId]);

  useEffect(() => { load(); }, [load]);

  const buy = async (plan) => {
    const isCurrent = sub?.plan_tier === plan.tier;
    const price = Number(plan.monthly_price);
    const isFree = Number.isFinite(price) && price === 0;  // NaN ≠ free
    const action = isCurrent ? 'Продлить' : 'Перейти на';
    const msg = isFree
      ? `${action} тариф «${plan.name}» (бесплатно)?`
      : `${action} тариф «${plan.name}»? Спишется ${fmtMoney(price)} с баланса, доступ +30 дней.`;
    if (!window.confirm(msg)) return;
    setBusy(plan.id);
    try {
      const res = await apiFetch(`/api/v1/clubs/${clubId}/subscription/buy/`, {
        method: 'POST', body: JSON.stringify({ plan: plan.id }),
      });
      toast(`Тариф «${res.plan}» активен до ${fmtDate(res.expires_at)}`, { type: 'success' });
      load();
    } catch (e) {
      toast(e.body?.plan || e.body?.balance || e.body?.error || e.message || 'Ошибка', { type: 'error' });
    } finally { setBusy(null); }
  };

  const st = STATUS[sub?.status] || STATUS.expired;
  const left = daysLeft(sub?.expires_at);
  const lowBalance = sub?.expires_at && left != null && left <= 5;

  if (loading) return <div style={{ padding: 40, color: 'var(--text-muted)' }}>Загрузка…</div>;

  return (
    <div style={{ padding: '20px 24px', maxWidth: 1000 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
        <Crown size={22} />
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Подписка и баланс</h1>
        <button className="btn btn-secondary" style={{ fontSize: 12, marginLeft: 'auto' }} onClick={load}>
          <RefreshCw size={13} /> Обновить
        </button>
      </div>

      {/* Top cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14, marginBottom: 18 }}>
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 12, padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 13 }}>
            <Wallet size={15} /> Баланс клуба
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, marginTop: 6 }}>{fmtMoney(wallet.balance)}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
            Пополняется администратором платформы. С него оплачивается тариф.
          </div>
        </div>
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 12, padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 13 }}>
            <Clock size={15} /> Текущий тариф
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 6 }}>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{sub?.plan || '—'}</div>
            <span style={{ fontSize: 12, fontWeight: 600, color: st.color,
              background: st.color + '22', padding: '2px 10px', borderRadius: 999 }}>{st.label}</span>
          </div>
          <div style={{ fontSize: 12, color: lowBalance ? '#f59e0b' : 'var(--text-muted)', marginTop: 4 }}>
            {sub?.expires_at ? `Действует до ${fmtDate(sub.expires_at)}${left != null ? ` · осталось ${left} дн.` : ''}` : 'Нет активной подписки'}
          </div>
        </div>
        <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 12, padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)', fontSize: 13 }}>
            <Crown size={15} /> Использование ПК
          </div>
          {(() => {
            const u = wallet.pc_usage || { used: 0, limit: 0, over: false };
            const limitLabel = u.limit > 0 ? u.limit : '∞';
            return (
              <>
                <div style={{ fontSize: 28, fontWeight: 800, marginTop: 6, color: u.over ? '#ef4444' : 'var(--text-main)' }}>
                  {u.used} <span style={{ fontSize: 16, fontWeight: 400, color: 'var(--text-muted)' }}>/ {limitLabel}</span>
                </div>
                <div style={{ fontSize: 11, color: u.over ? '#ef4444' : 'var(--text-muted)', marginTop: 4 }}>
                  {u.over ? 'Превышен лимит тарифа — обновите план' : (u.limit > 0 ? `Можно добавить ещё ${Math.max(0, u.limit - u.used)} ПК` : 'Без ограничений по ПК')}
                </div>
              </>
            );
          })()}
        </div>
      </div>

      {lowBalance && (
        <div style={{ display: 'flex', gap: 10, background: 'rgba(245,158,11,0.1)', border: '1px solid #f59e0b',
          borderRadius: 10, padding: '12px 16px', marginBottom: 18, fontSize: 13 }}>
          <AlertCircle size={18} color="#f59e0b" style={{ flexShrink: 0 }} />
          Подписка скоро закончится. Продлите тариф, чтобы не потерять доступ к управлению.
        </div>
      )}

      {/* Plans */}
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase',
        letterSpacing: '0.5px', marginBottom: 10 }}>Тарифы</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 14, marginBottom: 24 }}>
        {plans.map(p => {
          const current = sub?.plan_tier === p.tier;
          return (
            <div key={p.id} style={{ background: 'var(--bg-panel)',
              border: `1px solid ${current ? '#6366f1' : 'var(--border-color)'}`, borderRadius: 12, padding: 18,
              position: 'relative' }}>
              {current && (
                <span style={{ position: 'absolute', top: 12, right: 12, fontSize: 10, fontWeight: 700,
                  color: '#6366f1', background: 'rgba(99,102,241,0.15)', padding: '2px 8px', borderRadius: 999 }}>
                  Текущий
                </span>
              )}
              <div style={{ fontSize: 18, fontWeight: 700 }}>{p.name}</div>
              <div style={{ fontSize: 24, fontWeight: 800, margin: '6px 0' }}>
                {Number(p.monthly_price) > 0 ? fmtMoney(p.monthly_price) : 'Бесплатно'}
                {Number(p.monthly_price) > 0 && <span style={{ fontSize: 13, fontWeight: 400, color: 'var(--text-muted)' }}> / мес</span>}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
                <Check size={12} style={{ verticalAlign: 'middle' }} /> {p.max_pcs > 0 ? `до ${p.max_pcs} ПК` : 'Без лимита ПК'}
              </div>
              <button className={current ? 'btn btn-secondary' : 'btn btn-primary'}
                style={{ width: '100%', justifyContent: 'center', opacity: busy === p.id ? 0.6 : 1 }}
                disabled={busy === p.id} onClick={() => buy(p)}>
                {busy === p.id ? '…' : current ? 'Продлить (+30 дн)' : 'Перейти'}
              </button>
            </div>
          );
        })}
      </div>

      {/* History */}
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase',
        letterSpacing: '0.5px', marginBottom: 10 }}>История операций</div>
      <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 12, overflow: 'hidden' }}>
        {wallet.transactions.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>Операций пока нет</div>
        ) : wallet.transactions.map(t => (
          <div key={t.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '11px 16px', borderBottom: '1px solid var(--border-color)', fontSize: 13 }}>
            <div>
              <span style={{ fontWeight: 600 }}>
                {t.type === 'topup' ? 'Пополнение' : t.type === 'charge' ? 'Списание (подписка)' : t.type === 'refund' ? 'Возврат' : 'Корректировка'}
              </span>
              {t.comment && <span style={{ color: 'var(--text-muted)' }}> · {t.comment}</span>}
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{new Date(t.created_at).toLocaleString('ru-RU')}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontWeight: 700, color: Number(t.amount) >= 0 ? '#10b981' : '#ef4444' }}>
                {Number(t.amount) >= 0 ? '+' : ''}{fmtMoney(t.amount)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Баланс: {fmtMoney(t.balance_after)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Subscription;
