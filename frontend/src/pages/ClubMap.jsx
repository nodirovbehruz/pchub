import { useState, useEffect, useCallback } from 'react';
import { Plus, Layers, AlertTriangle, MonitorOff, Power, X as XIcon, RefreshCw, Wrench, Move, Map, Grid3x3 } from 'lucide-react';
import SessionStartModal from '../components/SessionStartModal';
import PcContextMenu from '../components/PcContextMenu';
import PcActionModal from '../components/PcActionModal';
import FloorPlan from '../components/FloorPlan';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

// Normalize REST computer object → component-friendly shape
const norm = (pc) => ({
  ...pc,
  alias: pc.name || String(pc.pc_number || pc.id),
  online: (pc.status || '').toLowerCase() === 'online',
  status: (pc.status || 'offline').toLowerCase(),
  groupId: pc.group_id ?? pc.group ?? null,
  cpuModel: pc.cpu_model,
  ramTotalGb: pc.ram_total_gb,
  gpuModel: pc.gpu_model,
  ipAddress: pc.ip_address,
  activeUser: pc.active_user || null,
});

const STATUS_STYLE = (pc) => {
  if (pc?.online || pc?.status === 'online') {
    return { border: '#7c3aed', bg: 'rgba(124,58,237,0.30)', text: '#fff', accent: '#a78bfa' };
  }
  if (pc?.status === 'maintenance') {
    return { border: '#cc6600', bg: 'rgba(204,102,0,0.18)', text: '#fbbf24', accent: '#f59e0b' };
  }
  if (pc?.status === 'shell_down' || pc?.status === 'no_link') {
    return { border: '#dc2626', bg: 'rgba(220,38,38,0.15)', text: '#ef4444', accent: '#ef4444' };
  }
  return { border: 'rgba(255,255,255,0.08)', bg: 'rgba(20,24,35,0.5)', text: 'rgba(255,255,255,0.55)', accent: 'rgba(255,255,255,0.3)' };
};

// ── PcTile ──────────────────────────────────────────────────────────────────
const PcTile = ({ pc, selected, onClick, onContextMenu, onDoubleClick, techMode, onDragStart }) => {
  const { border, bg, text, accent } = STATUS_STYLE(pc);
  const isOnline = pc?.online || pc?.status === 'online';
  const isMaint  = pc?.status === 'maintenance';

  return (
    <div
      draggable={techMode}
      onDragStart={techMode ? onDragStart : undefined}
      onClick={onClick}
      onContextMenu={onContextMenu}
      onDoubleClick={onDoubleClick}
      title={techMode ? 'Перетащи в другую зону' : pc.alias}
      style={{
        width: '92px', height: '54px', borderRadius: '8px',
        border: `2px solid ${selected ? '#fff' : border}`,
        background: bg,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 10px', cursor: techMode ? 'grab' : 'pointer', userSelect: 'none',
        boxShadow: selected ? '0 0 0 3px rgba(99,102,241,0.45)' : (isMaint ? '0 0 0 2px rgba(204,102,0,0.3)' : 'none'),
        transition: 'all 0.12s ease', position: 'relative',
        opacity: techMode ? 0.92 : 1,
      }}
    >
      <span style={{ fontSize: '18px', fontWeight: 700, color: text }}>{pc.alias}</span>
      {techMode ? (
        <Move size={14} color="rgba(255,255,255,0.4)" />
      ) : isMaint ? (
        <AlertTriangle size={16} color={accent} />
      ) : pc?.status === 'shell_down' || pc?.status === 'no_link' ? (
        <XIcon size={16} color={accent} />
      ) : (
        <Power size={16} color={accent} style={{ opacity: isOnline ? 1 : 0.5 }} />
      )}
    </div>
  );
};

// ── ClubMap ─────────────────────────────────────────────────────────────────
const ClubMap = () => {
  const [hosts, setHosts]                   = useState([]);
  const [groups, setGroups]                 = useState([]);
  const [loading, setLoading]               = useState(true);
  const [selectedPcs, setSelectedPcs]       = useState(new Set());
  const [ctxMenu, setCtxMenu]               = useState(null);
  const [infoPc, setInfoPc]                 = useState(null);
  const [isSessionModalOpen, setIsSessionModalOpen] = useState(false);
  const [sessionPc, setSessionPc]           = useState(null);
  const [actionModal, setActionModal]       = useState(null);
  const [techMode, setTechMode]             = useState(false);
  const [draggedPcId, setDraggedPcId]       = useState(null);
  const [dragOverZone, setDragOverZone]     = useState(null);
  const [mapView, setMapView]               = useState('plan'); // 'plan' | 'zones'
  const { toast } = useToast();

  const clubId  = localStorage.getItem('active_club_id');
  const clubName = localStorage.getItem('active_club_name') || 'Клуб';

  const load = useCallback(async () => {
    if (!clubId) { setLoading(false); return; }
    try {
      const [pcJson, grJson] = await Promise.all([
        apiFetch(`/api/v1/computers/?club=${clubId}`),
        apiFetch(`/api/v1/computers/groups/?club=${clubId}`),
      ]);
      setHosts((pcJson.results || pcJson || []).map(norm));
      setGroups(grJson.results || grJson || []);
    } catch (e) {
      console.error('ClubMap load error', e);
    } finally {
      setLoading(false);
    }
  }, [clubId]);

  useEffect(() => {
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, [load]);

  // ── Drag & Drop ──────────────────────────────────────────────────────────
  const handleDragStart = (pc) => {
    setDraggedPcId(pc.id);
  };

  const handleDragOver = (e, zoneId) => {
    e.preventDefault();
    setDragOverZone(zoneId);
  };

  const handleDrop = async (e, targetGroupId) => {
    e.preventDefault();
    setDragOverZone(null);
    if (!draggedPcId) return;
    const pc = hosts.find(h => h.id === draggedPcId);
    if (!pc) return;
    // same zone — no-op
    if (String(pc.groupId) === String(targetGroupId)) { setDraggedPcId(null); return; }

    // Optimistic update
    setHosts(prev => prev.map(h =>
      h.id === draggedPcId
        ? { ...h, groupId: targetGroupId === '__ungrouped' ? null : targetGroupId }
        : h
    ));
    setDraggedPcId(null);

    try {
      await apiFetch(`/api/v1/computers/${draggedPcId}/position/`, {
        method: 'PATCH',
        body: JSON.stringify({ group: targetGroupId === '__ungrouped' ? null : targetGroupId }),
      });
    } catch (e) {
      toast('Ошибка перемещения: ' + e.message, { type: 'error' });
      load(); // revert
    }
  };

  // ── Maintenance toggle ───────────────────────────────────────────────────
  const toggleMaintenance = async (pc) => {
    const newStatus = pc.status === 'maintenance' ? 'offline' : 'maintenance';
    setHosts(prev => prev.map(h => h.id === pc.id ? { ...h, status: newStatus, online: false } : h));
    try {
      await apiFetch(`/api/v1/computers/${pc.id}/position/`, {
        method: 'PATCH',
        // BUGFIX: backend ComputerStatus choices are UPPERCASE; sending the
        // normalized lowercase status failed validation ("invalid status") → 400,
        // so maintenance toggle always errored. Send the canonical uppercase value.
        body: JSON.stringify({ status: newStatus.toUpperCase() }),
      });
      toast(`ПК-${pc.alias}: ${newStatus === 'maintenance' ? '🔧 Обслуживание' : '✅ Офлайн'}`, { type: 'info' });
    } catch (e) {
      toast('Ошибка: ' + e.message, { type: 'error' });
      load();
    }
  };

  // ── Context menu & actions ───────────────────────────────────────────────
  const handleCreateGroup = async () => {
    const name = prompt('Название новой зоны');
    if (!name?.trim()) return;
    const color = '#' + Math.floor(Math.random() * 0xffffff).toString(16).padStart(6, '0');
    try {
      await apiFetch('/api/v1/computers/groups/', {
        method: 'POST',
        body: JSON.stringify({ club: Number(clubId), name: name.trim(), color, position: groups.length }),
      });
      load();
    } catch (e) {
      toast('Ошибка создания зоны: ' + (e.body?.detail || e.message), { type: 'error' });
    }
  };

  const handleTileClick = (pc, e) => {
    if (techMode) {
      // In tech mode single click toggles maintenance
      toggleMaintenance(pc);
      return;
    }
    if (e.ctrlKey || e.metaKey) {
      setSelectedPcs(prev => {
        const next = new Set(prev);
        if (next.has(pc.id)) next.delete(pc.id); else next.add(pc.id);
        return next;
      });
    } else {
      setSelectedPcs(new Set([pc.id]));
    }
  };

  const handleTileContext = (pc, e) => {
    e.preventDefault();
    if (techMode) return; // no context menu in tech mode
    setCtxMenu({ x: e.clientX, y: e.clientY, pc });
    if (!selectedPcs.has(pc.id)) setSelectedPcs(new Set([pc.id]));
  };

  const handleMenuSelect = async (actionId, pc) => {
    setCtxMenu(null);
    switch (actionId) {
      case 'select-tariff':
        setSessionPc(pc);
        setIsSessionModalOpen(true);
        break;
      case 'stop-session':
        if (!window.confirm(`Завершить сеанс на ПК-${pc.alias}?`)) return;
        try {
          await apiFetch('/api/v1/computers/admin/session/stop/', {
            method: 'POST',
            body: JSON.stringify({ computer_id: pc.id }),
          });
          toast(`Сеанс на ПК-${pc.alias} завершён`, { type: 'success' });
          load();
        } catch (e) {
          toast('Ошибка: ' + e.message, { type: 'error' });
        }
        break;
      case 'topup':    setActionModal({ mode: 'topup', pc }); break;
      case 'booking':  setActionModal({ mode: 'booking', pc }); break;
      case 'notify':   setActionModal({ mode: 'notify', pc }); break;
      case 'power':    setActionModal({ mode: 'power', pc }); break;
      case 'postpay':  setActionModal({ mode: 'postpay', pc }); break;
      case 'penalty':  setActionModal({ mode: 'penalty', pc }); break;
      case 'transfer': setActionModal({ mode: 'transfer', pc }); break;
      case 'control':  setActionModal({ mode: 'control', pc }); break;
      case 'shell':    setActionModal({ mode: 'shell', pc }); break;
      default: break;
    }
  };

  // ── Computed ─────────────────────────────────────────────────────────────
  const hostsByGroup = groups.reduce((acc, g) => {
    acc[g.id] = hosts.filter(pc => String(pc.groupId) === String(g.id));
    return acc;
  }, {});
  const ungrouped = hosts.filter(pc => !pc.groupId || !groups.find(g => String(g.id) === String(pc.groupId)));

  const onlineCount      = hosts.filter(pc => pc.online).length;
  const maintenanceCount = hosts.filter(pc => pc.status === 'maintenance').length;
  const offlineCount     = hosts.filter(pc => !pc.online && pc.status !== 'maintenance').length;

  // ── Zone renderer ─────────────────────────────────────────────────────────
  const renderZone = (group, pcs) => {
    const zoneId  = group.id;
    const isOver  = dragOverZone === String(zoneId);
    return (
      <div key={group.id}
        onDragOver={techMode ? (e) => handleDragOver(e, String(zoneId)) : undefined}
        onDrop={techMode ? (e) => handleDrop(e, String(zoneId)) : undefined}
        onDragLeave={techMode ? () => setDragOverZone(null) : undefined}
        style={{
          marginBottom: '40px',
          border: isOver ? '2px dashed #6366f1' : '2px dashed transparent',
          borderRadius: '12px', padding: isOver ? '8px' : '0', transition: 'all 0.15s',
          background: isOver ? 'rgba(99,102,241,0.06)' : 'transparent',
        }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px', paddingLeft: '4px' }}>
          <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '3px', background: group.color || '#6366f1' }} />
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-light)' }}>{group.name}</span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', padding: '2px 8px', background: 'rgba(255,255,255,0.04)', borderRadius: '10px' }}>
            {pcs.length} ПК
          </span>
          {isOver && (
            <span style={{ fontSize: '11px', color: '#6366f1', fontWeight: 600 }}>Перетащи сюда ↓</span>
          )}
        </div>
        {pcs.length > 0 ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', padding: '8px 4px' }}>
            {pcs.map(pc => (
              <PcTile key={pc.id} pc={pc} selected={selectedPcs.has(pc.id)}
                techMode={techMode}
                onDragStart={() => handleDragStart(pc)}
                onClick={(e) => handleTileClick(pc, e)}
                onContextMenu={(e) => handleTileContext(pc, e)}
                onDoubleClick={() => !techMode && setInfoPc(pc)} />
            ))}
          </div>
        ) : (
          <div style={{ padding: '20px', color: isOver ? '#6366f1' : 'var(--text-muted)', fontSize: '12px', textAlign: 'center',
            background: 'rgba(255,255,255,0.02)', border: `1px dashed ${isOver ? '#6366f1' : 'rgba(255,255,255,0.08)'}`,
            borderRadius: '10px', maxWidth: '400px', transition: 'all 0.15s' }}>
            {isOver ? '⬇ Отпусти здесь' : 'В этой зоне пока нет ПК'}
          </div>
        )}
      </div>
    );
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '0 24px' }}>
      {/* ── Toolbar ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn btn-secondary" onClick={load}
            style={{ width: '32px', height: '32px', padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <RefreshCw size={14} />
          </button>
          {maintenanceCount > 0 && (
            <span style={{ fontSize: '11px', padding: '4px 10px', borderRadius: '999px',
              background: 'rgba(204,102,0,0.15)', color: '#f59e0b',
              display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <AlertTriangle size={12} /> В обслуживании — {maintenanceCount}
            </span>
          )}
          {offlineCount > 0 && (
            <span style={{ fontSize: '11px', padding: '4px 10px', borderRadius: '999px',
              background: 'rgba(220,38,38,0.12)', color: '#ef4444',
              display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <MonitorOff size={12} /> Офлайн — {offlineCount}
            </span>
          )}
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            {loading ? 'Загрузка…' : `${clubName} · ${onlineCount} активных / ${hosts.length} всего`}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          {/* View toggle: План зала / Зоны */}
          <div style={{ display: 'flex', gap: '2px', padding: '2px', borderRadius: '9px',
            background: 'var(--bg-dark)', border: '1px solid var(--border-color)' }}>
            <button onClick={() => setMapView('plan')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '5px',
                padding: '5px 12px', borderRadius: '7px', fontSize: '12px', cursor: 'pointer',
                fontFamily: 'inherit', fontWeight: 500, border: 'none',
                background: mapView === 'plan' ? 'var(--accent)' : 'transparent',
                color: mapView === 'plan' ? '#fff' : 'var(--text-muted)' }}>
              <Map size={13} /> План зала
            </button>
            <button onClick={() => setMapView('zones')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '5px',
                padding: '5px 12px', borderRadius: '7px', fontSize: '12px', cursor: 'pointer',
                fontFamily: 'inherit', fontWeight: 500, border: 'none',
                background: mapView === 'zones' ? 'var(--accent)' : 'transparent',
                color: mapView === 'zones' ? '#fff' : 'var(--text-muted)' }}>
              <Grid3x3 size={13} /> Зоны
            </button>
          </div>

          {/* Technical mode toggle — only in zones view */}
          {mapView === 'zones' && (
            <button
              onClick={() => { setTechMode(v => !v); setSelectedPcs(new Set()); }}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px',
                padding: '6px 14px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer',
                fontFamily: 'inherit', fontWeight: 500,
                background: techMode ? 'rgba(251,191,36,0.15)' : 'var(--bg-dark)',
                border: `1px solid ${techMode ? '#f59e0b' : 'var(--border-color)'}`,
                color: techMode ? '#f59e0b' : 'var(--text-muted)' }}>
              <Wrench size={14} />
              {techMode ? 'Выйти из тех. режима' : 'Тех. режим'}
            </button>
          )}
          {mapView === 'zones' && (
            <button className="btn btn-secondary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              onClick={handleCreateGroup}>
              <Layers size={14} /> Создать группу
            </button>
          )}
          <button className="btn btn-primary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            onClick={() => toast('ПК добавляются через регистрацию агента на компьютере', { type: 'info' })}>
            <Plus size={14} /> Добавить ПК
          </button>
        </div>
      </div>

      {/* Technical mode hint bar */}
      {mapView === 'zones' && techMode && (
        <div style={{ marginBottom: '16px', padding: '10px 16px', borderRadius: '10px',
          background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.3)',
          fontSize: '13px', color: '#fbbf24', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          <span>🔧 <strong>Технический режим</strong></span>
          <span>• <strong>Перетащи</strong> тайл в другую зону для смены группы</span>
          <span>• <strong>Клик</strong> по тайлу — переключить Обслуживание ↔ Офлайн</span>
        </div>
      )}

      {/* ── Floor plan view ── */}
      {mapView === 'plan' && (
        <FloorPlan
          clubId={clubId}
          hosts={hosts}
          onPcClick={(pc) => setInfoPc(pc)}
          onPcContext={(pc, e) => handleTileContext(pc, e)}
        />
      )}

      {/* ── Zones (list) view ── */}
      {mapView === 'zones' && (
        <div
          onClick={(e) => { if (e.target === e.currentTarget) setSelectedPcs(new Set()); }}
          onDragOver={techMode ? (e) => handleDragOver(e, '__ungrouped') : undefined}
          onDrop={techMode ? (e) => handleDrop(e, '__ungrouped') : undefined}
          style={{ minHeight: 'calc(100vh - 260px)',
            background: 'radial-gradient(circle at 50% 30%, rgba(99,102,241,0.04), transparent 70%)',
            padding: '24px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.04)' }}>
          {loading && (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px' }}>Загрузка…</div>
          )}
          {!loading && groups.length === 0 && hosts.length === 0 && (
            <div style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '60px', textAlign: 'center',
              border: '1px dashed rgba(255,255,255,0.1)', borderRadius: '12px' }}>
              Зон и ПК пока нет. Нажмите «Создать группу» для зонирования клуба.
            </div>
          )}
          {!loading && groups.map(group => renderZone(group, hostsByGroup[group.id] || []))}
          {ungrouped.length > 0 && renderZone({ id: '__ungrouped', name: 'Без группы', color: '#64748b' }, ungrouped)}
        </div>
      )}

      {/* ── Multi-select action bar ── */}
      {selectedPcs.size > 1 && !techMode && (
        <div style={{ position: 'fixed', bottom: '20px', left: '50%', transform: 'translateX(-50%)',
          background: 'var(--bg-panel)', border: '1px solid rgba(99,102,241,0.4)',
          borderRadius: '14px', padding: '12px 20px', display: 'flex', gap: '12px', alignItems: 'center',
          boxShadow: '0 12px 28px rgba(0,0,0,0.5)', zIndex: 500 }}>
          <span style={{ fontSize: '13px', color: 'var(--text-light)' }}>
            Выбрано: <strong>{selectedPcs.size} ПК</strong>
          </span>
          <button className="btn btn-secondary" style={{ fontSize: '12px' }}
            onClick={async () => {
              if (!window.confirm(`Перезагрузить ${selectedPcs.size} выбранных ПК?`)) return;
              try {
                const res = await apiFetch('/api/v1/computers/admin/commands/bulk/', {
                  method: 'POST',
                  body: JSON.stringify({
                    computer_ids: Array.from(selectedPcs),
                    command_type: 'reboot',
                    club: clubId,
                  }),
                });
                toast(`Перезагрузка отправлена на ${res?.commands_created ?? selectedPcs.size} ПК`, { type: 'success' });
                setSelectedPcs(new Set());
              } catch (e) {
                toast('Ошибка: ' + (e.message || 'не удалось отправить команду'), { type: 'error' });
              }
            }}>Перезагрузить</button>
          <button className="btn btn-secondary" style={{ fontSize: '12px' }}
            onClick={() => toast('Массовое уведомление — в разработке', { type: 'info' })}>Уведомление</button>
          <button className="btn btn-secondary" style={{ fontSize: '12px' }}
            onClick={() => setSelectedPcs(new Set())}>Отмена</button>
        </div>
      )}

      {/* ── Context menu ── */}
      {ctxMenu && (
        <PcContextMenu x={ctxMenu.x} y={ctxMenu.y} pc={ctxMenu.pc} isShiftOpen={true}
          onSelect={handleMenuSelect} onClose={() => setCtxMenu(null)} />
      )}

      {/* ── Info modal ── */}
      {infoPc && (
        <div onClick={(e) => { if (e.target === e.currentTarget) setInfoPc(null); }}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 800 }}>
          <div style={{ background: 'var(--bg-panel)', borderRadius: '14px', padding: '24px',
            minWidth: '380px', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 style={{ margin: 0 }}>ПК-{infoPc.alias}</h3>
              <button className="icon-btn" onClick={() => setInfoPc(null)}><XIcon size={18} /></button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
              {infoPc.cpuModel && <div><span style={{ color: 'var(--text-muted)' }}>Процессор:</span> {infoPc.cpuModel}</div>}
              {infoPc.ramTotalGb && <div><span style={{ color: 'var(--text-muted)' }}>ОЗУ:</span> {infoPc.ramTotalGb} ГБ</div>}
              {infoPc.gpuModel && <div><span style={{ color: 'var(--text-muted)' }}>GPU:</span> {infoPc.gpuModel}</div>}
              {infoPc.ipAddress && <div><span style={{ color: 'var(--text-muted)' }}>IP:</span> <code>{infoPc.ipAddress}</code></div>}
              {infoPc.activeUser && <div><span style={{ color: 'var(--text-muted)' }}>Пользователь:</span> {infoPc.activeUser}</div>}
              <div><span style={{ color: 'var(--text-muted)' }}>Статус:</span> {infoPc.status}</div>
            </div>
            {/* Maintenance quick toggle */}
            <button
              onClick={() => { toggleMaintenance(infoPc); setInfoPc(null); }}
              style={{ marginTop: '16px', width: '100%', padding: '8px', borderRadius: '8px',
                border: '1px solid rgba(251,191,36,0.4)', background: 'rgba(251,191,36,0.08)',
                color: '#fbbf24', cursor: 'pointer', fontSize: '13px', fontFamily: 'inherit',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
              <Wrench size={14} />
              {infoPc.status === 'maintenance' ? 'Снять обслуживание' : 'Поставить на обслуживание'}
            </button>
          </div>
        </div>
      )}

      {/* ── Session modal ── */}
      <SessionStartModal isOpen={isSessionModalOpen}
        onClose={() => { setIsSessionModalOpen(false); setSessionPc(null); load(); }}
        pc={sessionPc} />

      {/* ── Action modal ── */}
      <PcActionModal mode={actionModal?.mode} pc={actionModal?.pc}
        isOpen={!!actionModal} onClose={() => { setActionModal(null); load(); }} />
    </div>
  );
};

export default ClubMap;
