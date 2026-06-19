import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Home, Monitor, LayoutGrid, Calendar, ShoppingCart,
  Wallet, Users, List, Box, Percent, UserCheck,
  MessageSquare, Grid, TrendingUp, Settings as SettingsIcon,
  ChevronDown, ChevronRight, Tag, Package, Wrench, Layers,
  Sun, Moon, LogOut, MessageCircle, BadgePercent, Gift, Trophy, Newspaper, Gamepad2, Bell, Crown,
  ChevronUp,
} from 'lucide-react';
import { apiFetch } from './api/client';

import Dashboard from './pages/Dashboard';
import ClubMap from './pages/ClubMap';
import Analytics from './pages/Analytics';
import Booking from './pages/Booking';
import Login from './pages/Login';
import Clients from './pages/Clients';
import Employees from './pages/Employees';
import Products from './pages/Products';
import StoreServices from './pages/StoreServices';
import SettingsPage from './pages/Settings';
import Tariffs from './pages/Tariffs';
import Computers from './pages/Computers';
import Discounts from './pages/loyalty/Discounts';
import Promocodes from './pages/loyalty/Promocodes';
import Cashback from './pages/loyalty/Cashback';
import Achievements from './pages/loyalty/Achievements';
import Payments from './pages/Payments';
import Logs from './pages/Logs';
import Reviews from './pages/Reviews';
import News from './pages/content/News';
import Tasks from './pages/content/Tasks';
import Apps from './pages/content/Apps';
import Combos from './pages/Combos';
import Shop from './pages/Shop';
import Orders from './pages/Orders';
import Chat from './pages/Chat';
import AdminCalls from './pages/AdminCalls';
import Cabinet from './pages/Cabinet';
import Subscription from './pages/Subscription';
import ShiftModal from './components/ShiftModal';
import PromisedPaymentModal from './components/PromisedPaymentModal';
import PlatformApp from './platform/PlatformApp';
import { decodeJwt, logout as apiLogout } from './api/client';

/* ─── Profile dropdown ────────────────────────────────────────────────── */
function ProfileMenu({ user, theme, toggleTheme, isShiftOpen, onOpenShift, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef();

  useEffect(() => {
    if (!open) return;
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const roleLabel = user?.role === 'owner' ? 'Владелец'
    : user?.role === 'platform_admin' ? 'Platform Admin'
    : 'Менеджер';

  const menuRow = (icon, label, onClick, danger = false, right = null) => (
    <div onClick={() => { onClick(); setOpen(false); }}
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '10px 16px', cursor: 'pointer', fontSize: '13px',
        color: danger ? '#ef4444' : 'var(--text-main)',
        userSelect: 'none',
      }}
      onMouseEnter={e => e.currentTarget.style.background = danger ? 'rgba(239,68,68,0.08)' : 'var(--hover-overlay)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
      <span style={{ color: danger ? '#ef4444' : 'var(--text-muted)', display: 'flex' }}>{icon}</span>
      <span style={{ flex: 1 }}>{label}</span>
      {right}
    </div>
  );

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      {/* Avatar button */}
      <div onClick={() => setOpen(v => !v)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
          padding: '4px 8px', borderRadius: 10,
          background: open ? 'var(--hover-overlay)' : 'transparent',
        }}>
        <div style={{
          width: 34, height: 34, borderRadius: '50%',
          background: 'var(--bg-panel)', border: '2px solid var(--border-color)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <UserCheck size={16} color="var(--text-muted)" />
        </div>
        {open
          ? <ChevronUp size={14} color="var(--text-muted)" />
          : <ChevronDown size={14} color="var(--text-muted)" />}
      </div>

      {/* Dropdown panel */}
      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 6px)', right: 0,
          background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
          borderRadius: 12, boxShadow: '0 12px 32px rgba(0,0,0,0.45)',
          minWidth: 230, zIndex: 300, overflow: 'hidden',
        }}>
          {/* User info header */}
          <div style={{
            padding: '14px 16px', borderBottom: '1px solid var(--border-color)',
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <div style={{
              width: 38, height: 38, borderRadius: '50%',
              background: 'var(--bg-dark)', border: '2px solid var(--border-color)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <UserCheck size={18} color="var(--accent)" />
            </div>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600 }}>{user?.username || 'admin'}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{roleLabel}</div>
            </div>
            {isShiftOpen && (
              <span style={{
                marginLeft: 'auto', fontSize: '10px', fontWeight: 700,
                padding: '3px 8px', borderRadius: 6,
                background: 'rgba(16,185,129,0.15)', color: '#10b981',
                whiteSpace: 'nowrap',
              }}>
                На смене
              </span>
            )}
          </div>

          {/* Theme toggle row */}
          <div
            onClick={toggleTheme}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '10px 16px', fontSize: '13px', cursor: 'pointer',
              borderBottom: '1px solid var(--border-color)',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <span style={{ color: 'var(--text-muted)', display: 'flex' }}>
              {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
            </span>
            <span style={{ flex: 1 }}>Переключить тему</span>
            {/* Mini toggle visual */}
            <div style={{
              width: 34, height: 18, borderRadius: 9, position: 'relative',
              background: theme === 'light' ? 'var(--accent)' : 'rgba(255,255,255,0.15)',
              transition: 'background 0.2s', flexShrink: 0,
            }}>
              <div style={{
                position: 'absolute', top: 2,
                left: theme === 'light' ? 'calc(100% - 16px)' : 2,
                width: 14, height: 14, borderRadius: '50%',
                background: '#fff', transition: 'left 0.2s',
              }} />
            </div>
          </div>

          {/* Shift action */}
          {menuRow(
            isShiftOpen ? <Moon size={15} /> : <Sun size={15} />,
            isShiftOpen ? 'Сдать смену' : 'Открыть смену',
            onOpenShift,
          )}

          {/* Logout */}
          <div style={{ borderTop: '1px solid var(--border-color)' }}>
            {menuRow(<LogOut size={15} />, 'Выйти', onLogout, true)}
          </div>
        </div>
      )}
    </div>
  );
}

// SmartShell sidebar order: Дашборд / Компьютеры / Карта клуба / Бронирование /
// Магазин / Платежи / Клиенты / Логи / [Товары и услуги ▾] /
// [Система лояльности ▾] / Сотрудники / Отзывы клиентов / [Контент ▾] /
// Аналитика / Настройки
const MAIN_NAV = [
  { id: 'dashboard',  label: 'Дашборд',       icon: Home },
  { id: 'computers',  label: 'Компьютеры',    icon: Monitor },
  { id: 'map',        label: 'Карта клуба',   icon: LayoutGrid },
  { id: 'booking',    label: 'Бронирование',  icon: Calendar },
  { id: 'shop',       label: 'Магазин',       icon: ShoppingCart },
  { id: 'orders',     label: 'Заказы',        icon: Box },
  { id: 'chat',       label: 'Чат',           icon: MessageCircle },
  { id: 'payments',   label: 'Платежи',       icon: Wallet },
  { id: 'clients',    label: 'Клиенты',       icon: Users },
  { id: 'logs',       label: 'Логи',          icon: List },
];

const STORE_SUB = [
  { id: 'tariffs',         label: 'Тарифы',        icon: Tag },
  { id: 'products',        label: 'Товары',        icon: Package },
  { id: 'store-services',  label: 'Услуги',        icon: Wrench },
  { id: 'combos',          label: 'Комбо-наборы',  icon: Layers },
];

const LOYALTY_SUB = [
  { id: 'discounts',     label: 'Скидки',       icon: BadgePercent },
  { id: 'promocodes',    label: 'Промокоды',    icon: Gift },
  { id: 'cashback',      label: 'Кешбэк',       icon: Percent },
  { id: 'achievements',  label: 'Достижения',   icon: Trophy },
];

const CONTENT_SUB = [
  { id: 'apps',  label: 'Приложения',  icon: Gamepad2 },
  { id: 'news',  label: 'Новости',     icon: Newspaper },
];

const TAIL_NAV = [
  { id: 'employees',  label: 'Сотрудники',      icon: UserCheck },
  { id: 'reviews',    label: 'Отзывы клиентов', icon: MessageSquare },
  { id: 'calls',      label: 'Вызовы',          icon: Bell },
];

const FINAL_NAV = [
  { id: 'cabinet',      label: 'Мои клубы',  icon: Crown },
  { id: 'subscription', label: 'Подписка',   icon: BadgePercent },
  { id: 'analytics',    label: 'Аналитика',  icon: TrendingUp },
  { id: 'settings',     label: 'Настройки',  icon: SettingsIcon },
];

function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [storeExpanded, setStoreExpanded] = useState(false);
  const [loyaltyExpanded, setLoyaltyExpanded] = useState(false);
  const [contentExpanded, setContentExpanded] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem('pchub_theme') || 'dark');
  const [isShiftModalOpen, setIsShiftModalOpen] = useState(false);
  const [activeShift, setActiveShift] = useState(null);
  const [unansweredCalls, setUnansweredCalls] = useState(0);
  const [subscription, setSubscription] = useState(null); // null = loading, object = loaded
  const [showPromised, setShowPromised] = useState(false);
  const [userType, setUserType] = useState(null); // 'admin' = platform operator
  const [subBlocked, setSubBlocked] = useState(false); // 402 subscription_inactive

  // Listen for the subscription gate (402) → show a "renew" overlay.
  useEffect(() => {
    const onBlocked = () => setSubBlocked(true);
    window.addEventListener('subscription-inactive', onBlocked);
    return () => window.removeEventListener('subscription-inactive', onBlocked);
  }, []);

  // Restore session on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      const payload = decodeJwt(token);
      setUser({
        username: payload?.username || 'admin',
        userId: payload?.user_id || null,
        role: localStorage.getItem('active_club_role') || 'manager',
        clubName: localStorage.getItem('active_club_name') || '',
      });
      setIsAuthenticated(true);
    }
  }, []);

  // Determine if the logged-in user is a PLATFORM admin → show platform panel
  useEffect(() => {
    if (!isAuthenticated) return;
    apiFetch('/api/v1/accounts/profile/')
      .then(p => setUserType(p?.user_type || 'user'))
      .catch(() => setUserType('user'));
  }, [isAuthenticated]);

  // Poll shift status via REST
  const fetchShift = useCallback(async () => {
    try {
      const data = await apiFetch('/api/v1/billing/shifts/current/');
      setActiveShift(data.is_active ? data.shift : null);
    } catch {
      // silent — shift stays as-is
    }
  }, []);

  // Poll unanswered admin calls count
  const fetchCalls = useCallback(async () => {
    try {
      const clubId = localStorage.getItem('active_club_id');
      const data = await apiFetch(`/api/v1/sessions/admin-calls/${clubId ? `?club=${clubId}` : ''}`);
      const list = data.results || data || [];
      setUnansweredCalls(list.filter(c => !c.is_answered).length);
    } catch {
      // silent
    }
  }, []);

  // Fetch subscription status for the active club
  const fetchSubscription = useCallback(async () => {
    const clubId = localStorage.getItem('active_club_id');
    if (!clubId) { setSubscription(null); return; }
    try {
      const data = await apiFetch(`/api/v1/clubs/${clubId}/subscription/`);
      setSubscription(data);
    } catch {
      setSubscription(null); // on error — don't block
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchShift();
    fetchCalls();
    fetchSubscription();
    const t1 = setInterval(fetchShift, 10000);
    const t2 = setInterval(fetchCalls, 15000);
    const t3 = setInterval(fetchSubscription, 60000); // check every minute
    return () => { clearInterval(t1); clearInterval(t2); clearInterval(t3); };
  }, [isAuthenticated, fetchShift, fetchCalls, fetchSubscription]);

  const isShiftOpen = !!activeShift;

  const handleLogin = (userData) => {
    setUser(userData);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    apiLogout();
    setUser(null);
    setIsAuthenticated(false);
    setActivePage('dashboard');
  };

  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  // Platform-level admin: only allowed in the club panel via explicit impersonation.
  const impersonating = userType === 'admin' && localStorage.getItem('impersonate_mode');
  if (userType === 'admin' && !impersonating) {
    if (window.location.pathname !== '/platform') {
      window.location.href = '/platform';
      return null;
    }
    return <PlatformApp />;
  }

  const isStoreActive = STORE_SUB.some(p => p.id === activePage);
  const isLoyaltyActive = LOYALTY_SUB.some(p => p.id === activePage);
  const isContentActive = CONTENT_SUB.some(p => p.id === activePage);

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('pchub_theme', newTheme);
  };

  const renderNavItem = (item, opts = {}) => {
    const Icon = item.icon;
    const disabled = item.shiftRequired && !isShiftOpen;
    const hasBadge = item.id === 'calls' && unansweredCalls > 0;
    return (
      <div
        key={item.id}
        className={`nav-item ${activePage === item.id ? 'active' : ''}`}
        onClick={() => !disabled && setActivePage(item.id)}
        style={opts.style}
        title={disabled ? 'Откройте смену чтобы зайти' : undefined}
      >
        <Icon className="nav-icon" size={opts.iconSize || 16} />
        <span style={{ opacity: disabled ? 0.4 : 1, flex: 1 }}>{item.label}</span>
        {hasBadge && (
          <span style={{
            background: '#ef4444', color: '#fff', borderRadius: '999px',
            fontSize: '10px', fontWeight: 700, minWidth: '18px', height: '18px',
            lineHeight: '18px', textAlign: 'center', padding: '0 4px',
          }}>
            {unansweredCalls > 99 ? '99+' : unansweredCalls}
          </span>
        )}
      </div>
    );
  };

  const renderSubGroup = (label, mainIcon, items, expanded, setExpanded, isActive) => {
    const MainIcon = mainIcon;
    return (
      <>
        <div
          className={`nav-item ${isActive ? 'active' : ''}`}
          onClick={() => setExpanded(v => !v)}
          style={{ justifyContent: 'space-between' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MainIcon className="nav-icon" size={16} />
            {label}
          </div>
          {expanded || isActive ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
        {(expanded || isActive) && (
          <div style={{ paddingLeft: '16px' }}>
            {items.map(item =>
              renderNavItem(item, { style: { fontSize: '13px', paddingLeft: '8px' }, iconSize: 15 })
            )}
          </div>
        )}
      </>
    );
  };

  return (
    <div className="app-container" data-theme={theme}>
      {impersonating && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 2000,
          height: 36, background: 'linear-gradient(90deg,#6366f1,#a855f7)', color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14, fontSize: 13, fontWeight: 600 }}>
          🛡 Режим платформы — вы вошли как клуб «{localStorage.getItem('active_club_name') || ''}»
          <button onClick={() => {
              localStorage.removeItem('impersonate_mode');
              localStorage.removeItem('active_club_id');
              localStorage.removeItem('active_club_name');
              window.location.href = '/platform';
            }}
            style={{ background: 'rgba(255,255,255,0.2)', border: 'none', color: '#fff', cursor: 'pointer',
              borderRadius: 6, padding: '3px 12px', fontSize: 12, fontWeight: 600, fontFamily: 'inherit' }}>
            ← Вернуться в платформу
          </button>
        </div>
      )}
      <aside className="sidebar" style={impersonating ? { marginTop: 36 } : undefined}>
        <div className="brand">
          <div className="brand-icon">
            <Monitor size={20} />
          </div>
          <div>
            <span>PCHUB</span>
            <span
              style={{
                color: 'var(--text-muted)',
                fontSize: '10px',
                display: 'block',
                fontWeight: 500,
              }}
            >
              ADMIN
            </span>
          </div>
        </div>

        <div className="nav-menu">
          {MAIN_NAV.map(item => renderNavItem(item))}

          <hr style={{ borderColor: 'var(--border-color)', margin: '8px 10px', opacity: 0.4 }} />

          {renderSubGroup('Товары и услуги', Box, STORE_SUB,
            storeExpanded, setStoreExpanded, isStoreActive)}
          {renderSubGroup('Система лояльности', Percent, LOYALTY_SUB,
            loyaltyExpanded, setLoyaltyExpanded, isLoyaltyActive)}

          {TAIL_NAV.map(item => renderNavItem(item))}

          {renderSubGroup('Контент', Grid, CONTENT_SUB,
            contentExpanded, setContentExpanded, isContentActive)}

          <hr style={{ borderColor: 'var(--border-color)', margin: '8px 10px', opacity: 0.4 }} />

          {FINAL_NAV.map(item => renderNavItem(item))}
        </div>

        <div style={{
          marginTop: 'auto',
          padding: '12px',
          borderTop: '1px solid var(--border-color)',
          opacity: 0.7,
          fontSize: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          <MessageCircle size={14} />
          Чат поддержки
        </div>

        {/* Subscription badge — click for promised payment */}
        {subscription && (
          <div
            onClick={() => setShowPromised(true)}
            title="Управление подпиской / обещанный платёж"
            style={{ padding: '8px 12px 12px', cursor: 'pointer', fontSize: '11px',
              display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ padding: '2px 8px', borderRadius: '6px', fontWeight: 700,
              background: subscription.is_blocked ? 'rgba(239,68,68,0.15)'
                : subscription.status === 'promised' ? 'rgba(245,158,11,0.15)'
                : subscription.is_trial ? 'rgba(99,102,241,0.15)' : 'rgba(16,185,129,0.15)',
              color: subscription.is_blocked ? '#ef4444'
                : subscription.status === 'promised' ? '#f59e0b'
                : subscription.is_trial ? '#818cf8' : '#10b981' }}>
              {subscription.is_blocked ? 'Заблокирован'
                : subscription.status === 'promised' ? 'Обещанный платёж'
                : subscription.is_trial ? `Trial${subscription.trial_days_left != null ? ` — ${subscription.trial_days_left}д.` : ''}`
                : subscription.plan || 'Free'}
            </span>
          </div>
        )}
      </aside>

      <main className="main-content">
        <header className="top-header">
          <div className="page-title">
            <span style={{ color: 'var(--text-muted)' }}>
              {user?.clubName || 'Режим менеджера'}
            </span>
          </div>
          <div className="header-actions" style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            {isShiftOpen && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', marginRight: '8px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Касса</span>
                <span style={{ fontSize: '14px', fontWeight: 600, color: '#10b981' }}>
                  {/* Касса = деньги в ящике (нач. касса + наличная выручка + ПКО − РКО),
                      а не выручка. Раньше показывало total_revenue и игнорировало ордера. */}
                  {Number(activeShift?.expected_cash || 0).toLocaleString('ru-RU')} сум
                </span>
              </div>
            )}

            <button
              className={`btn ${isShiftOpen ? 'btn-secondary' : 'btn-primary'}`}
              style={{ borderColor: isShiftOpen ? '#ef4444' : '', color: isShiftOpen ? '#ef4444' : '' }}
              onClick={() => setIsShiftModalOpen(true)}
            >
              {isShiftOpen ? 'Закрыть смену' : 'Открыть смену'}
            </button>

            {/* Calls badge */}
            <button className="icon-btn" title="Вызовы оператора"
              onClick={() => setActivePage('calls')}
              style={{ position: 'relative' }}>
              <Bell size={20} />
              {unansweredCalls > 0 && (
                <span style={{
                  position: 'absolute', top: '-4px', right: '-4px',
                  background: '#ef4444', color: '#fff',
                  borderRadius: '999px', fontSize: '10px', fontWeight: 700,
                  minWidth: '16px', height: '16px', lineHeight: '16px',
                  textAlign: 'center', padding: '0 3px',
                }}>
                  {unansweredCalls > 99 ? '99+' : unansweredCalls}
                </span>
              )}
            </button>

            {/* Operator profile with dropdown */}
            <ProfileMenu
              user={user}
              theme={theme}
              toggleTheme={toggleTheme}
              isShiftOpen={isShiftOpen}
              onOpenShift={() => setIsShiftModalOpen(true)}
              onLogout={handleLogout}
            />
          </div>
        </header>

        <ShiftModal
          isOpen={isShiftModalOpen}
          onClose={() => setIsShiftModalOpen(false)}
          isShiftOpen={isShiftOpen}
          activeShift={activeShift}
          onShiftChange={fetchShift}
        />

        {showPromised && (
          <PromisedPaymentModal
            clubId={localStorage.getItem('active_club_id')}
            promised={subscription?.promised_payment}
            onClose={() => setShowPromised(false)}
            onSuccess={fetchSubscription}
          />
        )}

        <div className="page-body">
          {/* ── Subscription paywall ────────────────────────────────────── */}
          {subscription?.is_blocked && activePage !== 'cabinet' ? (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', height: '100%', padding: '40px 24px', textAlign: 'center',
            }}>
              <div style={{ fontSize: '56px', marginBottom: '16px' }}>🔒</div>
              <h2 style={{ margin: '0 0 8px', fontSize: '24px', fontWeight: 700, color: 'var(--text-light)' }}>
                Триальный период закончился
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '14px', maxWidth: '440px', lineHeight: 1.6, margin: '0 0 32px' }}>
                Доступ к панели управления клубом заблокирован. Выберите тариф чтобы продолжить работу.
              </p>

              {/* Plans */}
              <div style={{ display: 'flex', gap: '16px', marginBottom: '32px', flexWrap: 'wrap', justifyContent: 'center' }}>
                {[
                  { name: 'Starter', price: '1 490 сум/мес', pcs: 'до 20 ПК', color: '#6366f1',
                    features: ['Все базовые функции', 'Касса и смены', 'Клиентская база'] },
                  { name: 'Business', price: '2 990 сум/мес', pcs: 'Без ограничений', color: '#f59e0b',
                    features: ['Всё из Starter', 'Аналитика', 'Бонусы и постоплата', 'Приоритетная поддержка'] },
                ].map(plan => (
                  <div key={plan.name} style={{
                    background: 'var(--bg-panel)', border: `2px solid ${plan.color}`,
                    borderRadius: '16px', padding: '24px', width: '220px',
                  }}>
                    <div style={{ fontWeight: 700, fontSize: '18px', color: plan.color, marginBottom: '4px' }}>{plan.name}</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }}>{plan.pcs}</div>
                    <div style={{ fontSize: '20px', fontWeight: 800, marginBottom: '16px' }}>{plan.price}</div>
                    <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 0', textAlign: 'left' }}>
                      {plan.features.map(f => (
                        <li key={f} style={{ fontSize: '12px', color: 'var(--text-muted)', padding: '3px 0', display: 'flex', gap: '6px' }}>
                          <span style={{ color: plan.color }}>✓</span> {f}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
                <button className="btn btn-primary" style={{ padding: '10px 24px', fontSize: '14px' }}
                  onClick={() => setActivePage('cabinet')}>
                  Перейти в кабинет
                </button>
                {/* Promised payment — only offer if not already active */}
                {!subscription?.promised_payment?.active && (
                  <button
                    onClick={() => setShowPromised(true)}
                    style={{ padding: '10px 24px', fontSize: '14px', borderRadius: '8px', cursor: 'pointer',
                      fontFamily: 'inherit', fontWeight: 600,
                      background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.4)', color: '#f59e0b' }}>
                    ⏳ Обещанный платёж
                  </button>
                )}
                <a href="https://t.me/pchub_support" target="_blank" rel="noopener noreferrer"
                  style={{ padding: '10px 24px', fontSize: '14px', borderRadius: '8px', border: '1px solid var(--border-color)',
                    color: 'var(--text-muted)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
                  Написать в поддержку
                </a>
              </div>

              {subscription?.trial_until && (
                <p style={{ marginTop: '24px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  Триал истёк: {new Date(subscription.trial_until).toLocaleDateString('ru-RU')}
                </p>
              )}
            </div>
          ) : (
          <>
          {activePage === 'dashboard' && <Dashboard />}
          {activePage === 'computers' && <Computers />}
          {activePage === 'map' && <ClubMap />}
          {activePage === 'booking' && <Booking />}
          {activePage === 'shop' && <Shop />}
          {activePage === 'orders' && <Orders />}
          {activePage === 'chat' && <Chat />}
          {activePage === 'payments' && <Payments />}
          {activePage === 'clients' && <Clients />}
          {activePage === 'logs' && <Logs />}
          {/* Товары и услуги */}
          {activePage === 'tariffs' && <Tariffs />}
          {activePage === 'products' && <Products />}
          {activePage === 'store-services' && <StoreServices />}
          {activePage === 'combos' && <Combos />}
          {/* Лояльность */}
          {activePage === 'discounts' && <Discounts />}
          {activePage === 'promocodes' && <Promocodes />}
          {activePage === 'cashback' && <Cashback />}
          {activePage === 'achievements' && <Achievements />}
          {/* Прочее */}
          {activePage === 'employees' && <Employees />}
          {activePage === 'reviews' && <Reviews />}
          {activePage === 'calls' && <AdminCalls onCountChange={setUnansweredCalls} />}
          {activePage === 'apps' && <Apps />}
          {activePage === 'news' && <News />}
          {activePage === 'tasks' && <Tasks />}
          {activePage === 'cabinet' && <Cabinet onClubSwitch={fetchSubscription} onNavigate={setActivePage} />}
          {activePage === 'subscription' && <Subscription />}
          {activePage === 'analytics' && <Analytics />}
          {activePage === 'settings' && <SettingsPage />}
          </>
          )}
        </div>
      </main>

      {subBlocked && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', zIndex: 5000,
          display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 16,
            padding: 32, width: 440, maxWidth: '90vw', textAlign: 'center' }}>
            <div style={{ fontSize: 40, marginBottom: 8 }}>⏳</div>
            <h2 style={{ margin: '0 0 8px' }}>Подписка неактивна</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 22 }}>
              Управление клубом приостановлено. Продлите тариф, чтобы продолжить работу.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button className="btn btn-secondary" onClick={() => setSubBlocked(false)}>Закрыть</button>
              <button className="btn btn-primary"
                onClick={() => { setSubBlocked(false); setActivePage('subscription'); }}>
                Перейти к оплате
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
