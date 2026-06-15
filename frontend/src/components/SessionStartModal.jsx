import { useState, useEffect } from 'react';
import { X, Clock, Search, Check, Moon, Layers, CalendarClock } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from './Toast';
import './ShiftModal.css';

const TYPE_LABELS = {
  subscription: 'Абонемент',
  package:      'Пакетный',
  per_minute:   'Поминутный',
  fixed:        'Фиксированный',
};

const TYPE_COLORS = {
  subscription: '#fb923c',
  package:      '#38bdf8',
  per_minute:   '#a855f7',
  fixed:        '#ec4899',
};

const SessionStartModal = ({ isOpen, onClose, pc }) => {
  const { toast } = useToast();
  const [activeTab, setActiveTab]           = useState('registered');
  const [selectedTariff, setSelectedTariff] = useState(null);
  const [selectedUser, setSelectedUser]     = useState(null);
  const [paymentMethod, setPayMethod]       = useState('cash');
  const [userSearch, setUserSearch]         = useState('');
  const [userResults, setUserResults]       = useState([]);
  const [userSearching, setUserSearching]   = useState(false);
  const [tariffs, setTariffs]               = useState([]);
  const [tariffsLoading, setTariffsLoading] = useState(false);
  const [loading, setLoading]               = useState(false);

  const clubId = localStorage.getItem('active_club_id');

  // Load tariffs when modal opens
  useEffect(() => {
    if (!isOpen) return;
    setTariffsLoading(true);
    apiFetch(`/api/v1/billing/tariffs/${clubId ? `?club=${clubId}` : ''}`)
      .then(json => setTariffs(json.results || json || []))
      .catch(() => setTariffs([]))
      .finally(() => setTariffsLoading(false));
  }, [isOpen, clubId]);

  // Reset state on close
  useEffect(() => {
    if (!isOpen) {
      setSelectedTariff(null);
      setSelectedUser(null);
      setUserSearch('');
      setUserResults([]);
      setPayMethod('cash');
      setActiveTab('registered');
    }
  }, [isOpen]);

  // Debounced client search
  useEffect(() => {
    if (!userSearch || userSearch.length < 2) { setUserResults([]); return; }
    const t = setTimeout(async () => {
      setUserSearching(true);
      try {
        const json = await apiFetch(`/api/v1/accounts/users/search/?q=${encodeURIComponent(userSearch)}`);
        setUserResults(json.results || json || []);
      } catch { setUserResults([]); }
      finally { setUserSearching(false); }
    }, 300);
    return () => clearTimeout(t);
  }, [userSearch]);

  if (!isOpen || !pc) return null;

  const hour = new Date().getHours();
  const period = (hour >= 22 || hour < 8) ? 'night' : 'day';

  const resolvePrice = (tariff) => {
    if (!tariff?.prices?.length) return parseFloat(tariff?.price) || 0;
    if (pc?.groupId || pc?.group_id) {
      const gid = pc.groupId || pc.group_id;
      const exact = tariff.prices.find(p => String(p.group) === String(gid) && p.period === period);
      if (exact) return parseFloat(exact.price);
      const any = tariff.prices.find(p => String(p.group) === String(gid));
      if (any) return parseFloat(any.price);
    }
    return parseFloat(tariff.prices[0]?.price) || parseFloat(tariff.price) || 0;
  };

  const tariff = tariffs.find(t => String(t.id) === String(selectedTariff));
  const resolvedPrice = tariff ? resolvePrice(tariff) : 0;

  const handleStart = async () => {
    if (activeTab === 'registered' && !selectedUser) {
      toast('Выберите пользователя', { type: 'warning' });
      return;
    }
    if (!selectedTariff) {
      toast('Выберите тариф', { type: 'warning' });
      return;
    }
    setLoading(true);
    try {
      await apiFetch('/api/v1/computers/admin/session/start/', {
        method: 'POST',
        body: JSON.stringify({
          computer_id: pc.id,
          user_id: selectedUser?.id || null,
          tariff_id: selectedTariff || null,
          payment_method: paymentMethod,
          amount_paid: resolvedPrice,
        }),
      });
      toast('Сеанс успешно начат', { type: 'success' });
      onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка запуска сеанса', { type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content shift-modal" style={{ maxWidth: '580px' }}>
        <div className="modal-header">
          <h3>Размещение на ПК-{pc?.alias || pc?.name}</h3>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>

        <div className="modal-body" style={{ padding: 0 }}>
          {/* Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-color)', padding: '0 24px', background: 'var(--bg-dark)' }}>
            {[{ id: 'registered', label: '👤 Пользователь' }, { id: 'guest', label: '🎟 Без регистрации' }].map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                style={{ padding: '14px 16px', background: 'none', border: 'none', cursor: 'pointer',
                  borderBottom: `2px solid ${activeTab === tab.id ? 'var(--accent-blue)' : 'transparent'}`,
                  color: activeTab === tab.id ? 'var(--text-light)' : 'var(--text-muted)',
                  fontSize: '14px', fontWeight: 500, fontFamily: 'inherit', transition: 'all 0.15s' }}>
                {tab.label}
              </button>
            ))}
          </div>

          <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Client search */}
            {activeTab === 'registered' && (
              <div className="form-group" style={{ position: 'relative' }}>
                <label>Поиск пользователя</label>
                {selectedUser ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 14px',
                    background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: '8px' }}>
                    <div style={{ width: '32px', height: '32px', borderRadius: '50%',
                      background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: '#fff', fontWeight: 700, fontSize: '13px', flexShrink: 0 }}>
                      {(selectedUser.username || '?')[0].toUpperCase()}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, color: 'var(--text-light)' }}>{selectedUser.username}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        Баланс: {selectedUser.balance_formatted || '00:00'} · {selectedUser.phone || ''}
                      </div>
                    </div>
                    <button className="icon-btn" onClick={() => { setSelectedUser(null); setUserSearch(''); }}>
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="input-with-icon">
                      <Search size={16} />
                      <input type="text" className="large-input" placeholder="Логин, телефон..."
                        value={userSearch}
                        onChange={(e) => { setUserSearch(e.target.value); }} />
                    </div>
                    {userSearch.length >= 2 && (
                      <div style={{ position: 'absolute', top: '100%', left: 0, right: 0,
                        background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
                        borderRadius: '8px', zIndex: 100, boxShadow: '0 8px 24px rgba(0,0,0,0.4)', overflow: 'hidden' }}>
                        {userSearching && (
                          <div style={{ padding: '10px 14px', color: 'var(--text-muted)', fontSize: '13px' }}>Поиск…</div>
                        )}
                        {!userSearching && userResults.length === 0 && (
                          <div style={{ padding: '10px 14px', color: 'var(--text-muted)', fontSize: '13px' }}>Не найдено</div>
                        )}
                        {userResults.map(u => (
                          <div key={u.id}
                            style={{ padding: '10px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '10px' }}
                            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.04)'}
                            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                            onClick={() => { setSelectedUser(u); setUserSearch(''); setUserResults([]); }}>
                            <div style={{ width: '28px', height: '28px', borderRadius: '50%',
                              background: 'var(--bg-dark)', display: 'flex', alignItems: 'center',
                              justifyContent: 'center', fontSize: '12px', fontWeight: 700,
                              color: 'var(--accent-blue)', flexShrink: 0 }}>
                              {(u.username || '?')[0].toUpperCase()}
                            </div>
                            <div>
                              <div style={{ fontSize: '14px', fontWeight: 600 }}>{u.username}</div>
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                                ⏱ {u.balance_formatted || '00:00'} · {u.phone || ''}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Tariff grid */}
            <div>
              <label style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 500, marginBottom: '10px', display: 'block' }}>
                Тариф / Пакет
                <span style={{ marginLeft: '8px', fontSize: '11px' }}>
                  · {period === 'night' ? '🌙 ночной' : '☀️ дневной'}
                </span>
              </label>
              {tariffsLoading ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '20px' }}>Загрузка тарифов…</div>
              ) : tariffs.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '20px',
                  background: 'var(--bg-dark)', borderRadius: '8px' }}>
                  Нет тарифов. Создайте в разделе «Тарифы».
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  {tariffs.map(t => {
                    const price = resolvePrice(t);
                    const color = TYPE_COLORS[t.tariff_type] || '#6366f1';
                    const isSel = String(selectedTariff) === String(t.id);
                    return (
                      <div key={t.id} onClick={() => setSelectedTariff(t.id)}
                        style={{ padding: '12px 14px', borderRadius: '10px', cursor: 'pointer',
                          border: `1.5px solid ${isSel ? color : 'var(--border-color)'}`,
                          background: isSel ? `${color}1a` : 'var(--bg-dark)', transition: 'all 0.15s' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                          <span style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-light)' }}>{t.name}</span>
                          {isSel && <Check size={14} color={color} />}
                        </div>
                        <div style={{ fontSize: '10px', color, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '6px' }}>
                          {TYPE_LABELS[t.tariff_type] || t.tariff_type}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Clock size={11} /> {t.hours_display || `${t.minutes}м`}
                          </span>
                          <span style={{ fontSize: '13px', fontWeight: 700, color: '#10b981' }}>
                            {price === 0 ? 'По факту' : `${price} сум`}
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: '6px', marginTop: '6px', color: 'var(--text-muted)' }}>
                          {t.is_night && <Moon size={11} />}
                          {t.has_schedule && <CalendarClock size={11} />}
                          {t.tariff_type === 'subscription' && <Layers size={11} />}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Payment method */}
            <div className="form-group">
              <label>Способ оплаты</label>
              <div style={{ display: 'flex', gap: '8px' }}>
                {[
                  { v: 'cash',    l: '💵 Наличные' },
                  { v: 'card',    l: '💳 Карта' },
                  ...(activeTab === 'registered' ? [{ v: 'balance', l: '⏱ С баланса' }] : []),
                ].map(m => (
                  <button key={m.v} className={`method-btn ${paymentMethod === m.v ? 'active' : ''}`}
                    onClick={() => setPayMethod(m.v)} style={{ fontFamily: 'inherit' }}>
                    {m.l}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Отмена</button>
          <button className="btn btn-primary" onClick={handleStart} disabled={loading}>
            {loading ? 'Запуск...' : (activeTab === 'registered' ? 'Начать сеанс' : 'Посадить гостя')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SessionStartModal;
