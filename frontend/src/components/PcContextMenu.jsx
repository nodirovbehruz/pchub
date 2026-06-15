import { useEffect, useRef } from 'react';
import {
  Clock, Lock, Wallet, Calendar, Ban, ArrowLeftRight, X,
  Bell, Zap, Settings, MonitorOff, ChevronRight,
} from 'lucide-react';

// PCM menu per SmartShell «Постановка сеанса 1.png» — 11 items.
// `enabled` is computed from PC status: which actions make sense.
const MENU_BUILDER = (pc, isShiftOpen) => {
  const isOnline = pc?.online || pc?.status === 'online';
  const isMaintenance = pc?.status === 'maintenance';
  const canStartSession = !isOnline && !isMaintenance && isShiftOpen;
  const canActOnActive = isOnline && isShiftOpen;

  return [
    { id: 'select-tariff',  label: 'Выбрать тариф',     icon: Clock,            enabled: canStartSession },
    { id: 'postpay',        label: 'Постоплата',        icon: Lock,             enabled: canStartSession },
    { id: 'topup',          label: 'Пополнить депозит', icon: Wallet,           enabled: canActOnActive },
    { id: 'booking',        label: 'Бронирование',      icon: Calendar,         enabled: true,           hasSub: true },
    { id: 'penalty',        label: 'Штраф',             icon: Ban,              enabled: canActOnActive, hasSub: true },
    { id: 'transfer',       label: 'Смена места',       icon: ArrowLeftRight,   enabled: canActOnActive },
    { id: 'stop-session',   label: 'Завершить сеанс',   icon: X,                enabled: canActOnActive },
    { id: 'divider' },
    { id: 'notify',         label: 'Уведомление',       icon: Bell,             enabled: true },
    { id: 'power',          label: 'Электропитание',    icon: Zap,              enabled: true,           hasSub: true },
    { id: 'control',        label: 'Управление ПК',     icon: Settings,         enabled: true,           hasSub: true },
    { id: 'shell',          label: 'Шелл',              icon: MonitorOff,       enabled: true,           hasSub: true },
  ];
};

const PcContextMenu = ({ x, y, pc, isShiftOpen, onSelect, onClose }) => {
  const ref = useRef(null);

  useEffect(() => {
    const close = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', (e) => e.key === 'Escape' && onClose());
    return () => document.removeEventListener('mousedown', close);
  }, [onClose]);

  if (!pc) return null;
  const items = MENU_BUILDER(pc, isShiftOpen);

  return (
    <div
      ref={ref}
      style={{
        position: 'fixed',
        top: y,
        left: x,
        zIndex: 1000,
        minWidth: '220px',
        background: 'var(--bg-panel, #1a1f2e)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '10px',
        boxShadow: '0 12px 28px rgba(0,0,0,0.6)',
        padding: '6px',
      }}
    >
      {items.map((item, idx) => {
        if (item.id === 'divider') {
          return (
            <div key={idx} style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '6px 8px' }} />
          );
        }
        const Icon = item.icon;
        return (
          <div
            key={item.id}
            onClick={() => item.enabled && onSelect(item.id, pc)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '10px',
              padding: '8px 10px',
              borderRadius: '6px',
              cursor: item.enabled ? 'pointer' : 'not-allowed',
              color: item.enabled ? 'var(--text-light, white)' : 'var(--text-muted)',
              opacity: item.enabled ? 1 : 0.4,
              fontSize: '13px',
              transition: 'background 0.12s',
            }}
            onMouseEnter={(e) => {
              if (item.enabled) e.currentTarget.style.background = 'rgba(99,102,241,0.12)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Icon size={14} />
              {item.label}
            </div>
            {item.hasSub && <ChevronRight size={12} style={{ opacity: 0.5 }} />}
          </div>
        );
      })}
    </div>
  );
};

export default PcContextMenu;
