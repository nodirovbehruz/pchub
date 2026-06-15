import React, { useState } from 'react';
import { X, DollarSign, ShieldCheck, AlertTriangle } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from './Toast';
import './ShiftModal.css';

const ShiftModal = ({ isOpen, onClose, isShiftOpen, activeShift, onShiftChange }) => {
  const [cashStart, setCashStart] = useState('0');
  const [cashEnd, setCashEnd] = useState('0');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  if (!isOpen) return null;

  const handleOpen = async () => {
    setLoading(true);
    try {
      await apiFetch('/api/v1/billing/shifts/open/', {
        method: 'POST',
        body: JSON.stringify({ initial_cash: parseFloat(cashStart) || 0 }),
      });
      toast('Смена открыта', { type: 'success' });
      if (onShiftChange) onShiftChange();
      onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка открытия смены', { type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = async () => {
    setLoading(true);
    try {
      await apiFetch('/api/v1/billing/shifts/close/', {
        method: 'POST',
        body: JSON.stringify({ closing_cash: parseFloat(cashEnd) || 0, notes }),
      });
      toast('Смена закрыта', { type: 'success' });
      if (onShiftChange) onShiftChange();
      onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка закрытия смены', { type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const currentCash = activeShift?.expected_cash || activeShift?.expectedCash || 0;
  const cashRev = activeShift?.total_revenue_cash || activeShift?.totalRevenueCash || 0;

  return (
    <div className="modal-overlay">
      <div className="modal-content shift-modal">
        <div className="modal-header">
          <h3>{isShiftOpen ? 'Закрытие смены' : 'Открытие смены'}</h3>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>

        <div className="modal-body">
          {!isShiftOpen ? (
            <div className="shift-flow">
              <div className="info-block">
                <div className="info-icon good"><ShieldCheck size={24} /></div>
                <div>
                  <div className="info-title">Рабочий день: {new Date().toLocaleDateString('ru-RU')}</div>
                  <div className="info-subtitle">Оператор: <span style={{ color: 'var(--text-light)' }}>
                    {localStorage.getItem('active_club_role') || 'admin'}
                  </span></div>
                </div>
              </div>
              <div className="form-group">
                <label>Наличность в кассе на начало смены</label>
                <div className="input-with-icon">
                  <DollarSign size={16} />
                  <input type="number" value={cashStart}
                    onChange={(e) => setCashStart(e.target.value)}
                    className="large-input" />
                  <span className="currency">сум</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="shift-flow">
              <div className="info-block warning-block">
                <div className="info-icon warning"><AlertTriangle size={24} /></div>
                <div>
                  <div className="info-title">Внимание: закрытие смены</div>
                  <div className="info-subtitle">Убедитесь, что фактическая сумма совпадает с расчётной.</div>
                </div>
              </div>
              <div className="shift-stats-grid">
                <div className="stat-card">
                  <span className="stat-label">Оператор</span>
                  <span className="stat-value">{activeShift?.operator || '—'}</span>
                </div>
                <div className="stat-card">
                  <span className="stat-label">Выручка наличными</span>
                  <span className="stat-value good">+ {Number(cashRev).toLocaleString('ru-RU')} сум</span>
                </div>
                <div className="stat-card highlight">
                  <span className="stat-label">Ожидается в кассе</span>
                  <span className="stat-value">{Number(currentCash).toLocaleString('ru-RU')} сум</span>
                </div>
              </div>
              <div className="form-group">
                <label>Фактическая наличность (Инкассация)</label>
                <div className="input-with-icon">
                  <DollarSign size={16} />
                  <input type="number" placeholder={String(currentCash)} value={cashEnd}
                    onChange={(e) => setCashEnd(e.target.value)} className="large-input" />
                  <span className="currency">сум</span>
                </div>
              </div>
              <div className="form-group">
                <label>Комментарий менеджера</label>
                <textarea placeholder="Расход из кассы / Чаевые..." rows="2"
                  value={notes} onChange={(e) => setNotes(e.target.value)} />
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Отмена</button>
          {!isShiftOpen ? (
            <button className="btn btn-primary" onClick={handleOpen} disabled={loading}>
              {loading ? 'Открытие...' : 'Открыть смену'}
            </button>
          ) : (
            <button className="btn btn-primary danger-action" onClick={handleClose} disabled={loading}>
              {loading ? 'Закрытие...' : 'Завершить смену'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ShiftModal;
