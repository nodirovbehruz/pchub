import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Monitor, Gamepad2, Car, Glasses, Armchair, Coffee, Utensils, Shirt,
  Type, Minus, Square, MousePointer2, Save,
  ArrowRight, ArrowLeft, ArrowUp, ArrowDown, X,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from './Toast';

/* ── Cell size ── */
const CELL = 46;
const DEFAULT_COLS = 18;
const DEFAULT_ROWS = 13;

/* ── Object icons palette ── */
const OBJ_ICONS = {
  console: Gamepad2,
  racing:  Car,
  vr:      Glasses,
  sofa:    Armchair,
  table:   Square,
  hanger:  Shirt,
  food:    Utensils,
  drink:   Coffee,
};

/* ── Tools ── */
const TOOLS = [
  { id: 'select', icon: MousePointer2, label: 'Выбор / удалить' },
  { id: 'wall',   icon: Minus,         label: 'Стена' },
  { id: 'arrow',  icon: ArrowRight,    label: 'Проход / стрелка' },
  { id: 'label',  icon: Type,          label: 'Текст (зона)' },
  { id: 'pc',     icon: Monitor,       label: 'Компьютер' },
  { id: 'console',icon: Gamepad2,      label: 'Консоль' },
  { id: 'racing', icon: Car,           label: 'Гоночный симулятор' },
  { id: 'vr',     icon: Glasses,       label: 'VR' },
  { id: 'sofa',   icon: Armchair,      label: 'Диван' },
  { id: 'table',  icon: Square,        label: 'Стол' },
  { id: 'hanger', icon: Shirt,         label: 'Вешалка' },
  { id: 'food',   icon: Utensils,      label: 'Еда' },
  { id: 'drink',  icon: Coffee,        label: 'Напитки' },
];

const ARROW_DIRS = ['right', 'down', 'left', 'up'];
const ARROW_ICONS = { right: ArrowRight, left: ArrowLeft, up: ArrowUp, down: ArrowDown };

/* ── PC status colors (matches ClubMap) ── */
const pcColors = (pc) => {
  if (!pc) return { border: 'rgba(255,255,255,0.15)', bg: 'rgba(120,120,140,0.12)', text: 'var(--text-muted)' };
  // BUGFIX: normalize case here — the backend enum is UPPERCASE (ONLINE/MAINTENANCE);
  // this used to work only because ClubMap pre-lowercased. Fed raw REST data every PC
  // showed offline. (shell_down/no_link are not produced by the backend — kept as
  // defensive aliases only.)
  const st = (pc.status || '').toUpperCase();
  if (pc.online || st === 'ONLINE')
    return { border: '#7c3aed', bg: 'rgba(124,58,237,0.22)', text: '#c4b5fd' };
  if (st === 'MAINTENANCE')
    return { border: '#cc6600', bg: 'rgba(204,102,0,0.16)', text: '#fbbf24' };
  return { border: 'rgba(255,255,255,0.12)', bg: 'rgba(40,44,60,0.5)', text: 'rgba(255,255,255,0.55)' };
};

/* ─────────────────────────────────────────────────────────────────────────
   FloorPlan — visual grid editor + live view
   Props:
     clubId, hosts, onPcClick(pc, e), onPcContext(pc, e)
───────────────────────────────────────────────────────────────────────── */
const FloorPlan = ({ clubId, hosts, onPcClick, onPcContext }) => {
  const { toast } = useToast();
  const [editMode, setEditMode]   = useState(false);
  const [tool, setTool]           = useState('select');
  const [plan, setPlan]           = useState({ cols: DEFAULT_COLS, rows: DEFAULT_ROWS, items: {} });
  const [saving, setSaving]       = useState(false);
  const [dirty, setDirty]         = useState(false);
  const [pcPicker, setPcPicker]   = useState(null); // { x, y }
  const [dragKey, setDragKey]     = useState(null); // key of item being dragged

  /* ── Load saved plan from ClubSettings ── */
  const loadPlan = useCallback(async () => {
    if (!clubId) return;
    try {
      const res = await apiFetch(`/api/v1/clubs/${clubId}/settings/`);
      const fp = res?.data?.floor_plan;
      if (fp && fp.items) {
        setPlan({ cols: fp.cols || DEFAULT_COLS, rows: fp.rows || DEFAULT_ROWS, items: fp.items });
      }
    } catch { /* keep default */ }
  }, [clubId]);

  useEffect(() => { loadPlan(); }, [loadPlan]);

  /* ── Host lookup by id ── */
  const hostById = useMemo(() => {
    const m = {};
    (hosts || []).forEach(h => { m[String(h.id)] = h; });
    return m;
  }, [hosts]);

  /* PCs already placed on the map */
  const placedPcIds = useMemo(() => {
    const s = new Set();
    Object.values(plan.items).forEach(it => { if (it.t === 'pc') s.add(String(it.pcId)); });
    return s;
  }, [plan.items]);

  /* ── Mutators ── */
  const setCell = (key, value) => {
    setPlan(p => {
      const items = { ...p.items };
      if (value === null) delete items[key];
      else items[key] = value;
      return { ...p, items };
    });
    setDirty(true);
  };

  const handleCellClick = (x, y) => {
    const key = `${x},${y}`;
    const existing = plan.items[key];

    if (!editMode) {
      // View mode — only PCs are interactive
      if (existing?.t === 'pc') {
        const pc = hostById[String(existing.pcId)];
        if (pc && onPcClick) onPcClick(pc, { clientX: 0, clientY: 0 });
      }
      return;
    }

    // Edit mode
    if (tool === 'select') {
      // Click does nothing destructive now — move items by dragging,
      // delete via right-click. (Accidental delete-on-click was confusing.)
      return;
    }
    if (tool === 'wall') {
      setCell(key, existing?.t === 'wall' ? null : { t: 'wall' });
      return;
    }
    if (tool === 'arrow') {
      if (existing?.t === 'arrow') {
        // rotate
        const next = ARROW_DIRS[(ARROW_DIRS.indexOf(existing.dir) + 1) % 4];
        setCell(key, { t: 'arrow', dir: next });
      } else {
        setCell(key, { t: 'arrow', dir: 'right' });
      }
      return;
    }
    if (tool === 'label') {
      const text = window.prompt('Название зоны / подпись:', existing?.text || '');
      if (text === null) return;
      if (!text.trim()) { setCell(key, null); return; }
      setCell(key, { t: 'label', text: text.trim() });
      return;
    }
    if (tool === 'pc') {
      // Only place on an empty cell; existing PC cells are moved by dragging.
      if (!existing) setPcPicker({ x, y });
      return;
    }
    // Furniture / equipment object
    if (OBJ_ICONS[tool]) {
      setCell(key, { t: 'obj', icon: tool });
      return;
    }
  };

  const handleCellContext = (x, y, e) => {
    e.preventDefault();
    const key = `${x},${y}`;
    const it = plan.items[key];
    if (editMode) {
      // In edit mode right-click deletes any element on the cell.
      if (it) setCell(key, null);
      return;
    }
    if (it?.t === 'pc') {
      const pc = hostById[String(it.pcId)];
      if (pc && onPcContext) onPcContext(pc, e);
    }
  };

  const placePc = (pcId) => {
    if (!pcPicker) return;
    setCell(`${pcPicker.x},${pcPicker.y}`, { t: 'pc', pcId: String(pcId) });
    setPcPicker(null);
  };

  /* ── Drag to move any placed element (edit mode) ── */
  const handleDrop = (targetKey) => {
    if (!dragKey || dragKey === targetKey) { setDragKey(null); return; }
    setPlan(p => {
      const items = { ...p.items };
      const moving = items[dragKey];
      if (!moving) return p;
      const occupant = items[targetKey];
      items[targetKey] = moving;          // place at target
      if (occupant) items[dragKey] = occupant; // swap
      else delete items[dragKey];          // or vacate source
      return { ...p, items };
    });
    setDirty(true);
    setDragKey(null);
  };

  /* ── Grid resize ── */
  const addCol = () => { setPlan(p => ({ ...p, cols: Math.min(p.cols + 1, 30) })); setDirty(true); };
  const addRow = () => { setPlan(p => ({ ...p, rows: Math.min(p.rows + 1, 24) })); setDirty(true); };
  const delCol = () => { setPlan(p => ({ ...p, cols: Math.max(p.cols - 1, 6) })); setDirty(true); };
  const delRow = () => { setPlan(p => ({ ...p, rows: Math.max(p.rows - 1, 4) })); setDirty(true); };

  /* ── Save ── */
  const save = async (silent = false) => {
    if (!clubId) { toast('Клуб не выбран', { type: 'warning' }); return false; }
    setSaving(true);
    try {
      await apiFetch(`/api/v1/clubs/${clubId}/settings/`, {
        method: 'PATCH',
        body: JSON.stringify({ data: { floor_plan: plan } }),
      });
      if (!silent) toast('План зала сохранён', { type: 'success' });
      setDirty(false);
      return true;
    } catch (e) {
      toast('Ошибка сохранения: ' + (e.message || ''), { type: 'error' });
      return false;
    } finally {
      setSaving(false);
    }
  };

  /* ── Exit edit mode — auto-save if there are unsaved changes ── */
  const exitEdit = async () => {
    if (dirty) {
      const ok = await save();
      if (!ok) return; // stay in edit mode if save failed
    }
    setEditMode(false);
  };

  /* ── Render a single cell content ── */
  const renderCell = (x, y) => {
    const key = `${x},${y}`;
    const it = plan.items[key];
    if (!it) return null;

    if (it.t === 'pc') {
      const pc = hostById[String(it.pcId)];
      const c = pcColors(pc);
      return (
        <div style={{
          position: 'absolute', inset: '3px', borderRadius: '8px',
          border: `2px solid ${c.border}`, background: c.bg,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: '1px', cursor: editMode ? 'pointer' : 'pointer',
        }}>
          <span style={{ fontSize: '11px', fontWeight: 800, color: c.text, lineHeight: 1 }}>
            {pc ? pc.alias : '?'}
          </span>
          <Monitor size={15} color={c.text} />
        </div>
      );
    }
    if (it.t === 'wall') {
      return <div style={{ position: 'absolute', inset: '6px', borderRadius: '4px', background: 'rgba(160,165,180,0.45)' }} />;
    }
    if (it.t === 'arrow') {
      const A = ARROW_ICONS[it.dir] || ArrowRight;
      return (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <A size={20} color="rgba(255,255,255,0.45)" />
        </div>
      );
    }
    if (it.t === 'label') {
      return (
        <div style={{ position: 'absolute', top: '2px', left: '4px', whiteSpace: 'nowrap',
          fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', pointerEvents: 'none', zIndex: 5 }}>
          {it.text}
        </div>
      );
    }
    if (it.t === 'obj') {
      const I = OBJ_ICONS[it.icon] || Square;
      return (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <I size={20} color="rgba(200,205,220,0.55)" />
        </div>
      );
    }
    return null;
  };

  const cells = [];
  for (let y = 0; y < plan.rows; y++) {
    for (let x = 0; x < plan.cols; x++) {
      const key = `${x},${y}`;
      const hasItem = !!plan.items[key];
      const draggable = editMode && hasItem;
      cells.push(
        <div key={key}
          onClick={() => handleCellClick(x, y)}
          onContextMenu={(e) => handleCellContext(x, y, e)}
          draggable={draggable}
          onDragStart={draggable ? (e) => { setDragKey(key); e.dataTransfer.effectAllowed = 'move'; } : undefined}
          onDragOver={editMode ? (e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; } : undefined}
          onDrop={editMode ? (e) => { e.preventDefault(); handleDrop(key); } : undefined}
          style={{
            position: 'relative', width: CELL, height: CELL,
            border: '1px solid rgba(255,255,255,0.04)',
            background: dragKey === key ? 'rgba(124,58,237,0.18)' : 'rgba(255,255,255,0.015)',
            cursor: editMode ? (draggable ? 'grab' : (tool === 'select' ? 'default' : 'crosshair')) : 'default',
          }}>
          {renderCell(x, y)}
        </div>
      );
    }
  }

  return (
    <div>
      {/* ── Toolbar ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px', flexWrap: 'wrap' }}>
        <button
          onClick={() => editMode ? exitEdit() : setEditMode(true)}
          style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 14px',
            borderRadius: '8px', fontSize: '13px', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
            border: 'none', background: editMode ? '#10b981' : 'var(--hover-overlay)',
            color: editMode ? '#fff' : 'var(--text-muted)' }}>
          {editMode ? (dirty ? '✓ Сохранить и выйти' : '✓ Готово') : '✎ Редактировать карту'}
        </button>

        {editMode && (
          <>
            {/* Tools */}
            <div style={{ display: 'flex', gap: '3px', flexWrap: 'wrap', padding: '3px',
              background: 'var(--bg-panel)', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
              {TOOLS.map(t => {
                const I = t.icon;
                const active = tool === t.id;
                return (
                  <button key={t.id} title={t.label} onClick={() => setTool(t.id)}
                    style={{ width: '34px', height: '34px', borderRadius: '7px', border: 'none', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      background: active ? 'var(--accent)' : 'transparent',
                      color: active ? '#fff' : 'var(--text-muted)' }}>
                    <I size={16} />
                  </button>
                );
              })}
            </div>

            {/* Grid resize */}
            <div style={{ display: 'flex', gap: '3px', alignItems: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
              <span>Сетка:</span>
              <button className="icon-btn" title="Убрать столбец" onClick={delCol} style={{ width: 26, height: 26 }}>−</button>
              <span>{plan.cols}</span>
              <button className="icon-btn" title="Добавить столбец" onClick={addCol} style={{ width: 26, height: 26 }}>+</button>
              <span style={{ opacity: 0.4 }}>×</span>
              <button className="icon-btn" title="Убрать строку" onClick={delRow} style={{ width: 26, height: 26 }}>−</button>
              <span>{plan.rows}</span>
              <button className="icon-btn" title="Добавить строку" onClick={addRow} style={{ width: 26, height: 26 }}>+</button>
            </div>

            <button className="btn btn-primary" onClick={() => save(false)} disabled={saving}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px',
                opacity: dirty ? 1 : 0.6 }}>
              <Save size={13} /> {saving ? 'Сохранение…' : dirty ? 'Сохранить' : '✓ Сохранено'}
            </button>
          </>
        )}

        {editMode && (
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Инструмент: <strong>{TOOLS.find(t => t.id === tool)?.label}</strong>.
            {tool === 'pc'
              ? ' Кликните по пустой клетке, чтобы добавить ПК.'
              : ' Перетаскивайте элементы мышью, правый клик — удалить.'}
          </span>
        )}
      </div>

      {/* ── Grid canvas ── */}
      <div style={{ overflow: 'auto', border: '1px solid var(--border-color)', borderRadius: '12px',
        background: 'var(--bg-dark)', padding: '12px', maxWidth: '100%' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${plan.cols}, ${CELL}px)`,
          gridTemplateRows: `repeat(${plan.rows}, ${CELL}px)`,
          width: 'max-content',
        }}>
          {cells}
        </div>
      </div>

      {/* ── PC picker modal ── */}
      {pcPicker && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 950 }}
          onClick={e => e.target === e.currentTarget && setPcPicker(null)}>
          <div style={{ background: 'var(--bg-panel)', borderRadius: '14px', padding: '20px',
            width: '360px', maxWidth: '90vw', maxHeight: '70vh', overflow: 'auto',
            border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <h3 style={{ margin: 0, fontSize: '15px' }}>Выберите компьютер</h3>
              <button className="icon-btn" onClick={() => setPcPicker(null)}><X size={18} /></button>
            </div>
            {(hosts || []).filter(h => !placedPcIds.has(String(h.id))).length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                Все зарегистрированные ПК уже размещены на карте,<br />либо ПК ещё не подключены.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {(hosts || [])
                  .filter(h => !placedPcIds.has(String(h.id)))
                  .map(h => {
                    const c = pcColors(h);
                    return (
                      <button key={h.id} onClick={() => placePc(h.id)}
                        style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '9px 12px',
                          borderRadius: '8px', border: '1px solid var(--border-color)', cursor: 'pointer',
                          background: 'var(--hover-overlay)', fontFamily: 'inherit', textAlign: 'left' }}>
                        <div style={{ width: '28px', height: '28px', borderRadius: '6px',
                          border: `2px solid ${c.border}`, background: c.bg,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          fontSize: '11px', fontWeight: 800, color: c.text }}>
                          {h.alias}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '13px', fontWeight: 600 }}>{h.name || `ПК-${h.alias}`}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {h.online ? 'В сети' : h.status === 'maintenance' ? 'Обслуживание' : 'Офлайн'}
                          </div>
                        </div>
                      </button>
                    );
                  })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default FloorPlan;
