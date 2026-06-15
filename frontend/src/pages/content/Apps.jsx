import { useState, useEffect, useCallback } from 'react';
import {
  Gamepad2, Plus, Layers, ChevronDown, ChevronUp, X, GripVertical,
  Check, Trash2, Edit2, AlertCircle, Search, DownloadCloud, Monitor, RefreshCw,
} from 'lucide-react';
import { apiFetch } from '../../api/client';
import { useToast } from '../../components/Toast';

const PLATFORMS = [
  { value: 'steam', label: 'Steam' },
  { value: 'epic', label: 'Epic Games' },
  { value: 'riot', label: 'Riot' },
  { value: 'battlenet', label: 'Battle.net' },
  { value: 'origin', label: 'EA App' },
  { value: 'ubisoft', label: 'Ubisoft Connect' },
  { value: 'rockstar', label: 'Rockstar' },
  { value: 'local', label: 'Локально' },
];

const iStyle = {
  width: '100%', background: 'var(--bg-input)', border: '1px solid var(--border-input)',
  borderRadius: '8px', padding: '10px 12px', color: 'var(--text-main)', fontSize: '13px',
  fontFamily: 'inherit', boxSizing: 'border-box',
};

/* ── Game cover card ── */
const GameCard = ({ game, onEdit, onDelete, onInstall, onRelease }) => (
  <div style={{ width: '150px', flexShrink: 0 }}>
    <div style={{ position: 'relative', width: '150px', height: '200px', borderRadius: '12px',
      overflow: 'hidden', background: 'var(--bg-dark)', border: '1px solid var(--border-color)' }}>
      <img src={game.cover}
        alt={game.name}
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        onError={(e) => { e.target.src = `https://picsum.photos/seed/g${game.id}/300/400`; }} />
      {!game.is_active && (
        <div style={{ position: 'absolute', top: '6px', left: '6px', background: 'rgba(239,68,68,0.9)',
          color: '#fff', fontSize: '10px', fontWeight: 700, padding: '2px 7px', borderRadius: '6px' }}>
          Выключена
        </div>
      )}
      {/* hover actions */}
      <div className="game-card-actions" style={{ position: 'absolute', top: '6px', right: '6px',
        display: 'flex', gap: '4px', opacity: 0, transition: 'opacity 0.15s' }}>
        <button onClick={() => onInstall(game)} title="Установить / обновить на ПК"
          style={{ width: '26px', height: '26px', borderRadius: '7px', border: 'none', cursor: 'pointer',
            background: 'rgba(0,187,178,0.85)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <DownloadCloud size={13} />
        </button>
        <button onClick={() => onEdit(game)} title="Редактировать"
          style={{ width: '26px', height: '26px', borderRadius: '7px', border: 'none', cursor: 'pointer',
            background: 'rgba(0,0,0,0.6)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Edit2 size={13} />
        </button>
        <button onClick={() => onDelete(game)} title="Удалить"
          style={{ width: '26px', height: '26px', borderRadius: '7px', border: 'none', cursor: 'pointer',
            background: 'rgba(239,68,68,0.8)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Trash2 size={13} />
        </button>
      </div>
    </div>
    <div style={{ fontSize: '13px', fontWeight: 500, marginTop: '8px', textAlign: 'center',
      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
      {game.name}
    </div>
  </div>
);

/* ── Group accordion ── */
const GroupSection = ({ group, games, collapsed, onToggle, onEditGame, onDeleteGame, onInstallGame, onReleaseGame }) => (
  <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
    borderRadius: '12px', marginBottom: '12px', overflow: 'hidden' }}>
    <div onClick={onToggle}
      style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '16px 20px',
        cursor: 'pointer', userSelect: 'none' }}>
      <span style={{ fontSize: '15px', fontWeight: 700 }}>{group.name}</span>
      <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{games.length}</span>
      <div style={{ flex: 1 }} />
      {collapsed ? <ChevronDown size={18} color="var(--text-muted)" /> : <ChevronUp size={18} color="var(--text-muted)" />}
    </div>
    {!collapsed && (
      <div style={{ padding: '0 20px 20px' }}>
        {games.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
            Нет добавленных игр. Добавьте игры, чтобы привязать их к группе
          </div>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px' }}>
            {games.map(g => (
              <GameCard key={g.id} game={g} onEdit={onEditGame} onDelete={onDeleteGame} onInstall={onInstallGame} onRelease={onReleaseGame} />
            ))}
          </div>
        )}
      </div>
    )}
  </div>
);

/* ── Add / Edit game modal ── */
const GameModal = ({ game, groups, onClose, onSaved }) => {
  const { toast } = useToast();
  const isEdit = !!game;
  const [form, setForm] = useState({
    name: game?.name || '',
    platform: game?.platform || 'steam',
    app_id: game?.app_id || '',
    executable_path: game?.executable_path || '',
    version: game?.version || '1.0',
    category: game?.category || '',
    header_image: game?.header_image_url || '',
    is_active: game?.is_active ?? true,
  });
  const [loading, setLoading] = useState(false);
  const upd = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const save = async () => {
    if (!form.name.trim()) { toast('Введите название игры', { type: 'warning' }); return; }
    setLoading(true);
    try {
      const body = {
        name: form.name.trim(),
        platform: form.platform,
        app_id: form.app_id || null,
        executable_path: form.executable_path || null,
        version: (form.version || '1.0').trim(),
        category: form.category || null,
        is_active: form.is_active,
      };
      if (form.header_image) body.header_image_url = form.header_image.trim();
      if (isEdit) {
        await apiFetch(`/api/v1/games/admin/games/${game.slug}/update/`, {
          method: 'PATCH', body: JSON.stringify(body),
        });
        toast('Игра обновлена', { type: 'success' });
      } else {
        await apiFetch('/api/v1/games/admin/games/create/', {
          method: 'POST', body: JSON.stringify(body),
        });
        toast('Игра добавлена', { type: 'success' });
      }
      onSaved(); onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка сохранения', { type: 'error' });
    } finally { setLoading(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 900,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: '14px', padding: '24px',
        width: '440px', maxWidth: '90vw', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ margin: 0 }}>{isEdit ? 'Редактировать игру' : 'Добавить игру'}</h3>
          <button className="icon-btn" onClick={onClose}><X size={20} /></button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Название *</label>
            <input value={form.name} onChange={e => upd('name', e.target.value)} placeholder="GTA V" style={iStyle} autoFocus />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Платформа</label>
              <select value={form.platform} onChange={e => upd('platform', e.target.value)} style={iStyle}>
                {PLATFORMS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Группа</label>
              <select value={form.category} onChange={e => upd('category', e.target.value)} style={iStyle}>
                <option value="">Без группы</option>
                {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 140px', gap: '10px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                {form.platform === 'steam' ? 'Steam App ID' : 'ID приложения'}
              </label>
              <input value={form.app_id} onChange={e => upd('app_id', e.target.value)}
                placeholder={form.platform === 'steam' ? '271590' : 'ID'} style={iStyle} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Версия (необяз.)</label>
              <input value={form.version} onChange={e => upd('version', e.target.value)} placeholder="авто" style={iStyle} />
            </div>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '-8px' }}>
            Писать версию необязательно. Чтобы разослать обновление, на карточке игры нажмите 🔄 «Выпустить обновление» — версия поднимется сама.
          </div>

          {form.platform === 'local' && (
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Путь к .exe</label>
              <input value={form.executable_path} onChange={e => upd('executable_path', e.target.value)}
                placeholder="C:\Games\game.exe" style={iStyle} />
            </div>
          )}

          <div>
            <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>URL обложки (необязательно)</label>
            <input value={form.header_image} onChange={e => upd('header_image', e.target.value)}
              placeholder="https://...jpg" style={iStyle} />
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px' }}>
            <input type="checkbox" checked={form.is_active} onChange={e => upd('is_active', e.target.checked)}
              style={{ width: '16px', height: '16px' }} />
            Игра активна (видна клиентам)
          </label>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '24px' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Отмена</button>
          <button className="btn btn-primary" onClick={save} disabled={loading}>
            {loading ? 'Сохранение…' : isEdit ? 'Сохранить' : 'Добавить'}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ── Manage groups modal ── */
const GroupsModal = ({ groups, onClose, onChanged }) => {
  const { toast } = useToast();
  const [list, setList] = useState(groups.map(g => ({ ...g })));
  const [dragIdx, setDragIdx] = useState(null);

  const addGroup = async () => {
    try {
      const res = await apiFetch('/api/v1/games/categories/', {
        method: 'POST', body: JSON.stringify({ name: 'Новая группа' }),
      });
      setList(l => [...l, res]);
      onChanged();
    } catch (e) { toast(e.message || 'Ошибка', { type: 'error' }); }
  };

  const rename = async (id, name) => {
    setList(l => l.map(g => g.id === id ? { ...g, name } : g));
  };
  const commitRename = async (g) => {
    try { await apiFetch(`/api/v1/games/categories/${g.id}/`, { method: 'PATCH', body: JSON.stringify({ name: g.name }) }); onChanged(); }
    catch (e) { toast(e.message || 'Ошибка', { type: 'error' }); }
  };

  const remove = async (g) => {
    if (g.games_count > 0) { toast(`Нельзя удалить — в группе ${g.games_count} игр`, { type: 'warning' }); return; }
    if (!window.confirm(`Удалить группу «${g.name}»?`)) return;
    try {
      await apiFetch(`/api/v1/games/categories/${g.id}/`, { method: 'DELETE' });
      setList(l => l.filter(x => x.id !== g.id));
      onChanged();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка', { type: 'error' });
    }
  };

  const onDrop = async (idx) => {
    if (dragIdx === null || dragIdx === idx) { setDragIdx(null); return; }
    const next = [...list];
    const [moved] = next.splice(dragIdx, 1);
    next.splice(idx, 0, moved);
    setList(next);
    setDragIdx(null);
    try {
      await apiFetch('/api/v1/games/categories/reorder/', {
        method: 'POST', body: JSON.stringify({ order: next.map(g => g.id) }),
      });
      onChanged();
    } catch (e) { toast(e.message || 'Ошибка порядка', { type: 'error' }); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 900,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: '16px', padding: '28px',
        width: '460px', maxWidth: '92vw', maxHeight: '80vh', overflow: 'auto', border: '1px solid var(--border-color)' }}>
        <h3 style={{ margin: '0 0 6px', textAlign: 'center' }}>Управление группами</h3>
        <p style={{ margin: '0 0 18px', textAlign: 'center', fontSize: '13px', color: 'var(--text-muted)' }}>
          Перетащите группы в порядке, в котором хотите чтобы они отображались в шелле.
        </p>

        {/* warning */}
        <div style={{ display: 'flex', gap: '10px', padding: '12px 14px', borderRadius: '10px',
          background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)',
          marginBottom: '18px', alignItems: 'flex-start' }}>
          <AlertCircle size={16} color="#f59e0b" style={{ flexShrink: 0, marginTop: '1px' }} />
          <span style={{ fontSize: '12px', color: '#f59e0b', lineHeight: 1.5 }}>
            Группу нельзя удалить, если в ней есть игры. Сначала удалите игры.
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '18px' }}>
          {list.map((g, idx) => (
            <div key={g.id}
              draggable
              onDragStart={() => setDragIdx(idx)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => onDrop(idx)}
              style={{ display: 'flex', alignItems: 'center', gap: '10px',
                opacity: dragIdx === idx ? 0.5 : 1 }}>
              <GripVertical size={18} color="var(--text-muted)" style={{ cursor: 'grab', flexShrink: 0 }} />
              <div style={{ flex: 1, position: 'relative', background: 'var(--bg-dark)',
                border: '1px solid var(--border-input)', borderRadius: '10px', padding: '8px 12px' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Введите название</div>
                <input value={g.name}
                  onChange={e => rename(g.id, e.target.value)}
                  onBlur={() => commitRename(g)}
                  style={{ width: '100%', background: 'none', border: 'none', outline: 'none',
                    color: 'var(--text-main)', fontSize: '14px', fontFamily: 'inherit', padding: 0 }} />
              </div>
              <button onClick={() => commitRename(g)} title="Сохранить" className="icon-btn"><Check size={16} /></button>
              <button onClick={() => remove(g)} title="Удалить" className="icon-btn"
                style={{ color: g.games_count > 0 ? 'var(--text-muted)' : '#ef4444' }}>
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>

        <button onClick={addGroup}
          style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'none', border: 'none',
            color: 'var(--accent)', cursor: 'pointer', fontSize: '14px', fontFamily: 'inherit',
            padding: '0', marginBottom: '20px' }}>
          <Plus size={18} /> Добавить группу
        </button>

        <button className="btn btn-primary" onClick={onClose} style={{ width: '100%', padding: '12px' }}>
          Завершить редактирование
        </button>
      </div>
    </div>
  );
};

/* ── Install game on PCs (fleet broadcast) ── */
const InstallToPcsModal = ({ game, onClose }) => {
  const { toast } = useToast();
  const [pcs, setPcs]       = useState([]);
  const [target, setTarget] = useState('all');   // 'all' | 'selected'
  const [selected, setSelected] = useState(new Set());
  const [action, setAction] = useState('install'); // install | update | uninstall
  const [busy, setBusy]     = useState(false);
  const clubId = localStorage.getItem('active_club_id');
  const isSteam = (game.platform === 'steam');
  const noAppId = isSteam && !game.app_id;

  useEffect(() => {
    apiFetch(`/api/v1/computers/?club=${clubId}`)
      .then(j => setPcs(j.results || j || []))
      .catch(() => setPcs([]));
  }, [clubId]);

  const toggle = (id) => setSelected(s => {
    const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n;
  });

  const run = async () => {
    if (target === 'selected' && selected.size === 0) {
      toast('Выберите хотя бы один ПК', { type: 'warning' }); return;
    }
    setBusy(true);
    try {
      const res = await apiFetch('/api/v1/computers/admin/commands/bulk/', {
        method: 'POST',
        body: JSON.stringify({
          computer_ids: target === 'all' ? 'all' : Array.from(selected),
          command_type: action,
          game_id: game.id,
          club: clubId,
        }),
      });
      const n = res?.commands_created ?? 0;
      toast(`Команда «${action}» отправлена на ${n} ПК`, { type: 'success' });
      onClose();
    } catch (e) {
      toast(e.body ? Object.values(e.body).flat().join(', ') : (e.message || 'Ошибка'), { type: 'error' });
    } finally { setBusy(false); }
  };

  const ACTIONS = [
    { v: 'install',   label: 'Установить' },
    { v: 'update',    label: 'Обновить' },
    { v: 'uninstall', label: 'Удалить' },
  ];

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 950,
      display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: '14px', padding: '22px', width: '460px',
        maxWidth: '92vw', maxHeight: '82vh', overflow: 'auto', border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0, fontSize: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <DownloadCloud size={18} color="#00BBB2" /> {game.name} → на ПК
          </h3>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>

        {noAppId && (
          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', background: 'rgba(245,158,11,0.1)',
            border: '1px solid rgba(245,158,11,0.3)', borderRadius: '8px', padding: '10px 12px', marginBottom: '14px',
            fontSize: '12px', color: '#f59e0b' }}>
            <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '1px' }} />
            У Steam-игры не задан App ID — установка не сработает. Откройте «Редактировать» и впишите Steam App ID.
          </div>
        )}

        {/* Action */}
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>Действие</div>
        <div style={{ display: 'flex', gap: '6px', marginBottom: '16px' }}>
          {ACTIONS.map(a => (
            <button key={a.v} onClick={() => setAction(a.v)}
              style={{ flex: 1, padding: '8px', borderRadius: '8px', cursor: 'pointer', fontFamily: 'inherit',
                fontSize: '13px', fontWeight: 600, border: 'none',
                background: action === a.v ? 'var(--accent)' : 'var(--hover-overlay)',
                color: action === a.v ? '#fff' : 'var(--text-muted)' }}>
              {a.label}
            </button>
          ))}
        </div>

        {/* Target */}
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>Куда</div>
        <div style={{ display: 'flex', gap: '6px', marginBottom: '12px' }}>
          {[{ v: 'all', label: `Все ПК (${pcs.length})` }, { v: 'selected', label: 'Выбрать ПК' }].map(t => (
            <button key={t.v} onClick={() => setTarget(t.v)}
              style={{ flex: 1, padding: '8px', borderRadius: '8px', cursor: 'pointer', fontFamily: 'inherit',
                fontSize: '13px', fontWeight: 600, border: 'none',
                background: target === t.v ? 'var(--accent)' : 'var(--hover-overlay)',
                color: target === t.v ? '#fff' : 'var(--text-muted)' }}>
              {t.label}
            </button>
          ))}
        </div>

        {target === 'selected' && (
          <div style={{ maxHeight: '220px', overflow: 'auto', border: '1px solid var(--border-color)',
            borderRadius: '8px', padding: '6px', marginBottom: '14px' }}>
            {pcs.length === 0 ? (
              <div style={{ padding: '14px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                Нет зарегистрированных ПК
              </div>
            ) : pcs.map(pc => (
              <label key={pc.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '7px 8px',
                borderRadius: '6px', cursor: 'pointer', fontSize: '13px' }}>
                <input type="checkbox" checked={selected.has(pc.id)} onChange={() => toggle(pc.id)} />
                <Monitor size={14} color="var(--text-muted)" />
                {pc.name || `ПК-${pc.pc_number || pc.id}`}
                <span style={{ marginLeft: 'auto', fontSize: '11px',
                  color: pc.online || pc.status === 'online' ? '#22c55e' : 'var(--text-muted)' }}>
                  {pc.online || pc.status === 'online' ? 'в сети' : 'офлайн'}
                </span>
              </label>
            ))}
          </div>
        )}

        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '14px' }}>
          {isSteam
            ? 'Steam-игра: ПК выполнят steam://install — файлы тянутся через Steam (и LAN-кэш, если настроен).'
            : 'Не-Steam: ПК скачают установщик по ссылке игры (рекомендуется локальный сервер клуба).'}
        </div>

        <button className="btn btn-primary" onClick={run} disabled={busy || noAppId}
          style={{ width: '100%', opacity: (busy || noAppId) ? 0.6 : 1 }}>
          {busy ? 'Отправка…' : `Отправить на ${target === 'all' ? 'все ПК' : `${selected.size} ПК`}`}
        </button>
      </div>
    </div>
  );
};

/* ════════════════════════════════════════════════════════════════════════
   MAIN
═══════════════════════════════════════════════════════════════════════ */
const Apps = () => {
  const { toast } = useToast();
  const [games, setGames]       = useState([]);
  const [groups, setGroups]     = useState([]);
  const [loading, setLoading]   = useState(true);
  const [collapsed, setCollapsed] = useState({});
  const [search, setSearch]     = useState('');
  const [gameModal, setGameModal]   = useState(null); // {} for new, game for edit
  const [groupsModal, setGroupsModal] = useState(false);
  const [installGame, setInstallGame] = useState(null); // game → "install on PCs" modal

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [gJson, cJson] = await Promise.all([
        apiFetch('/api/v1/games/games/?page_size=500').catch(() => ({ results: [] })),
        apiFetch('/api/v1/games/categories/').catch(() => []),
      ]);
      setGames(gJson.results || gJson || []);
      setGroups(cJson.results || cJson || []);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const deleteGame = async (g) => {
    if (!window.confirm(`Удалить игру «${g.name}»?`)) return;
    try {
      await apiFetch(`/api/v1/games/admin/games/${g.slug}/delete/`, { method: 'DELETE' });
      toast('Игра удалена', { type: 'success' });
      load();
    } catch (e) { toast(e.message || 'Ошибка удаления', { type: 'error' }); }
  };

  // One-click «Выпустить обновление»: bumps the game version automatically and
  // updates online idle PCs now; busy PCs catch up in idle. No version typing.
  const releaseGame = async (g) => {
    if (!window.confirm(`Выпустить обновление «${g.name}» для всех ПК?`)) return;
    try {
      const res = await apiFetch(`/api/v1/games/admin/games/${g.slug}/release-update/`, { method: 'POST' });
      toast(res?.message || 'Обновление выпущено', { type: 'success' });
      load();
    } catch (e) { toast(e.body?.error || e.message || 'Ошибка', { type: 'error' }); }
  };

  // Filter by search
  const filtered = search
    ? games.filter(g => (g.name || '').toLowerCase().includes(search.toLowerCase()))
    : games;

  // Group games by category
  const byGroup = {};
  groups.forEach(gr => { byGroup[gr.id] = []; });
  const ungrouped = [];
  filtered.forEach(g => {
    if (g.category && byGroup[g.category]) byGroup[g.category].push(g);
    else ungrouped.push(g);
  });

  const collapseAll = () => {
    const all = {};
    groups.forEach(g => { all[g.id] = true; });
    all['__ungrouped'] = true;
    setCollapsed(all);
  };

  return (
    <div style={{ padding: '0 24px' }}>
      {/* hover CSS for cards */}
      <style>{`.game-card-actions { } div:hover > .game-card-actions { opacity: 1 !important; }`}</style>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Gamepad2 size={20} /> Приложения
          <span style={{ fontSize: '13px', fontWeight: 400, color: 'var(--text-muted)' }}>
            Игры {games.length}
          </span>
        </h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Поиск игры…"
              style={{ ...iStyle, width: '180px', paddingLeft: '32px' }} />
          </div>
          <button className="btn btn-secondary" onClick={collapseAll}>Свернуть все группы</button>
          <button className="btn btn-secondary" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            onClick={() => setGroupsModal(true)}>
            <Layers size={14} /> Управление группами
          </button>
          <button className="btn btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            onClick={() => setGameModal({})}>
            <Plus size={14} /> Добавить игру
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>Загрузка…</div>
      ) : (
        <>
          {groups.map(gr => (
            <GroupSection key={gr.id} group={gr} games={byGroup[gr.id] || []}
              collapsed={!!collapsed[gr.id]}
              onToggle={() => setCollapsed(c => ({ ...c, [gr.id]: !c[gr.id] }))}
              onEditGame={setGameModal} onDeleteGame={deleteGame} onInstallGame={setInstallGame} onReleaseGame={releaseGame} />
          ))}
          {/* Ungrouped */}
          <GroupSection
            group={{ id: '__ungrouped', name: 'Игры без группы' }}
            games={ungrouped}
            collapsed={!!collapsed['__ungrouped']}
            onToggle={() => setCollapsed(c => ({ ...c, __ungrouped: !c.__ungrouped }))}
            onEditGame={setGameModal} onDeleteGame={deleteGame} onInstallGame={setInstallGame} onReleaseGame={releaseGame} />
        </>
      )}

      {gameModal !== null && (
        <GameModal game={gameModal.id ? gameModal : null} groups={groups}
          onClose={() => setGameModal(null)} onSaved={load} />
      )}
      {groupsModal && (
        <GroupsModal groups={groups} onClose={() => { setGroupsModal(false); load(); }} onChanged={load} />
      )}
      {installGame && (
        <InstallToPcsModal game={installGame} onClose={() => setInstallGame(null)} />
      )}
    </div>
  );
};

export default Apps;
