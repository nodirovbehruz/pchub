import { useState } from 'react';
import { X, Clock, AlertTriangle, CalendarClock } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from './Toast';

/**
 * Обещанный платёж — 7-day subscription extension on credit (SmartShell-style).
 * Props: clubId, promised (current promised_payment object or null), onClose, onSuccess
 */
const PromisedPaymentModal = ({ clubId, promised, onClose, onSuccess }) => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const active = !!promised?.active;

  const activate = async () => {
    if (!clubId) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/clubs/${clubId}/promised-payment/`, { method: 'POST' });
      toast(res.message || 'Обещанный платёж подключён', { type: 'success' });
      onSuccess?.(); onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка', { type: 'error' });
    } finally { setLoading(false); }
  };

  const payDebt = async () => {
    if (!clubId) return;
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/clubs/${clubId}/promised-payment/`, { method: 'DELETE' });
      toast(res.message || 'Долг погашен', { type: 'success' });
      onSuccess?.(); onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка', { type: 'error' });
    } finally { setLoading(false); }
  };

  const POINTS = [
    { icon: Clock, title: 'Подключите услугу',
      text: 'Подписка будет продлена на 7 дней с сохранением текущих условий. За подключение услуги спишется 500 сум. Эту сумму нужно будет оплатить вместе с продлением подписки.' },
    { icon: CalendarClock, title: 'Оплатите долг в течение 30 дней',
      text: 'У вас есть 30 дней после окончания продлённой подписки (всего 37 дней с момента активации обещанного платежа), чтобы оплатить долг. Если долг не будет погашен, клуб будет заблокирован.' },
    { icon: AlertTriangle, title: 'Не затягивайте с оплатой',
      text: 'После окончания продлённой подписки клуб перейдёт на бесплатный тариф, если долг не будет оплачен вовремя.' },
  ];

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: '18px', padding: '28px',
        width: '430px', maxWidth: '92vw', maxHeight: '90vh', overflowY: 'auto',
        border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
          <h3 style={{ margin: 0, fontSize: '20px' }}>Обещанный платёж</h3>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>

        {active ? (
          /* ── Active promised payment — show status + pay debt ── */
          <>
            <div style={{ padding: '16px', borderRadius: '12px', marginBottom: '20px',
              background: promised.overdue ? 'rgba(239,68,68,0.08)' : 'rgba(99,102,241,0.08)',
              border: `1px solid ${promised.overdue ? 'rgba(239,68,68,0.3)' : 'rgba(99,102,241,0.3)'}` }}>
              <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '6px',
                color: promised.overdue ? '#ef4444' : '#818cf8' }}>
                {promised.overdue ? '⚠ Долг просрочен' : '✅ Обещанный платёж активен'}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                Сумма долга: <strong style={{ color: 'var(--text-main)' }}>{promised.fee} сум</strong><br/>
                Оплатить до: <strong style={{ color: 'var(--text-main)' }}>
                  {new Date(promised.due_at).toLocaleDateString('ru-RU')}</strong>
                {!promised.overdue && <> · осталось <strong>{promised.days_to_pay} дн.</strong></>}
              </div>
            </div>
            <button className="btn btn-primary" onClick={payDebt} disabled={loading}
              style={{ width: '100%', padding: '13px', fontSize: '14px' }}>
              {loading ? 'Оплата…' : `Погасить долг ${promised.fee} сум`}
            </button>
          </>
        ) : (
          /* ── Offer to activate ── */
          <>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, margin: '0 0 20px' }}>
              Если нет возможности оплатить подписку сейчас, мы продлим её за вас на 7 дней.
              Ваш клуб продолжит функционировать в прежнем режиме:
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
              {POINTS.map((p, i) => {
                const Icon = p.icon;
                return (
                  <div key={i} style={{ padding: '16px', borderRadius: '12px',
                    background: 'var(--hover-overlay)', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <Icon size={15} color="var(--accent)" />
                      <span style={{ fontSize: '14px', fontWeight: 600 }}>{p.title}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.6 }}>{p.text}</div>
                  </div>
                );
              })}
            </div>

            <button className="btn btn-primary" onClick={activate} disabled={loading}
              style={{ width: '100%', padding: '13px', fontSize: '14px' }}>
              {loading ? 'Подключение…' : 'Подключить'}
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default PromisedPaymentModal;
