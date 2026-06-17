import { useState, useEffect, useCallback } from 'react';
import { Layers, Plus, Trash2, Edit2, X, RefreshCw, Search, ChevronDown } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

const fmtMoney = (v) =>
  v == null || v === '' ? '—' : Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' сум';

// Combo name bounds — match the backend max_length=50 and the "2–50" UI hint.
const NAME_MIN = 2;
const NAME_MAX = 50;

const iStyle = {
  width: '100%', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
  borderRadius: 8, padding: '9px 12px', color: 'var(--text-main)',
  fontSize: 13, fontFamily: 'inherit', boxSizing: 'border-box',
};
const selStyle = { ...iStyle, appearance: 'none', paddingRight: 28, cursor: 'pointer' };

/* ─── Combo create/edit modal ────────────────────────────────────────────
 * Previously the form (a generic CrudPage) never sent tariff / computer_group
 * / items, so it created empty combos. This modal wires all of them. */
const ComboModal = ({ combo, products, tariffs, groups, clubId, onClose, onSaved }) => {
  const { toast } = useToast();
  const isEdit = !!combo?.id;
  const [form, setForm] = useState({
    name: combo?.name || '',
    sale_price: combo?.sale_price ?? '',
    base_price: combo?.base_price ?? 0,
    tariff: combo?.tariff ?? '',
    computer_group: combo?.computer_group ?? '',
    applies_discount: combo?.applies_discount ?? true,
    is_active: combo?.is_active ?? true,
  });
  // Component products with their quantity. Seed from the (read-only) nested
  // product_items the API returns when editing.
  const [items, setItems] = useState(
    (combo?.product_items || []).map(pi => ({ product: pi.product, qty: pi.qty || 1 }))
  );
  const [saving, setSaving] = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const addItem = () => setItems(list => [...list, { product: '', qty: 1 }]);
  const setItem = (idx, k, v) => setItems(list => list.map((it, i) => i === idx ? { ...it, [k]: v } : it));
  const removeItem = (idx) => setItems(list => list.filter((_, i) => i !== idx));

  const handleSave = async () => {
    const name = form.name.trim();
    // Enforce the 2–50 length client-side (the hint promised it; the backend
    // CharField caps at 50 but never rejected too-short names before save).
    if (name.length < NAME_MIN || name.length > NAME_MAX) {
      toast(`Название: от ${NAME_MIN} до ${NAME_MAX} символов`, { type: 'warning' });
      return;
    }
    if (form.sale_price === '' || Number(form.sale_price) < 0) {
      toast('Введите цену продажи', { type: 'warning' });
      return;
    }
    // SmartShell rule: a tariff requires a computer group (price depends on zone).
    if (form.tariff && !form.computer_group) {
      toast('Для тарифа выберите зал (зону)', { type: 'warning' });
      return;
    }
    const cleanItems = items
      .filter(it => it.product !== '' && it.product != null)
      .map(it => ({ product: Number(it.product), qty: Math.max(1, Number(it.qty) || 1) }));

    setSaving(true);
    try {
      const payload = {
        name,
        sale_price: Number(form.sale_price),
        base_price: form.base_price === '' ? 0 : Number(form.base_price),
        applies_discount: !!form.applies_discount,
        is_active: !!form.is_active,
        // Optional FKs: send the id when chosen, null to clear (was never sent → empty combos).
        tariff: form.tariff === '' ? null : Number(form.tariff),
        computer_group: form.computer_group === '' ? null : Number(form.computer_group),
        // Component products with qty.
        product_items: cleanItems,
        club: clubId ? Number(clubId) : null,
      };
      const body = JSON.stringify(payload);
      if (isEdit) {
        await apiFetch(`/api/v1/shops/combos/${combo.id}/`, { method: 'PATCH', body });
        toast('Комбо обновлено', { type: 'success' });
      } else {
        await apiFetch('/api/v1/shops/combos/', { method: 'POST', body });
        toast('Комбо создано', { type: 'success' });
      }
      onSaved();
      onClose();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка сохранения', { type: 'error' });
    } finally { setSaving(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 14, width: 480,
        maxHeight: '90vh', display: 'flex', flexDirection: 'column',
        border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
          <h3 style={{ margin: 0, fontSize: 15 }}>{isEdit ? 'Редактировать комбо' : 'Создать комбо'}</h3>
          <button className="icon-btn" onClick={onClose}><X size={15} /></button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '18px 20px' }}>
          {/* Name */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Название *</div>
            <input value={form.name} maxLength={NAME_MAX} placeholder="Комбо: Кола + 1 час"
              onChange={e => set('name', e.target.value)} style={iStyle} />
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{NAME_MIN}–{NAME_MAX} символов</div>
          </div>

          {/* Prices */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Цена продажи сум *</div>
              <input type="number" min="0" step="0.01" value={form.sale_price} placeholder="0"
                onChange={e => set('sale_price', e.target.value)} style={iStyle} />
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Базовая цена сум</div>
              <input type="number" min="0" step="0.01" value={form.base_price} placeholder="0"
                onChange={e => set('base_price', e.target.value)} style={iStyle} />
            </div>
          </div>

          {/* Optional tariff */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Тариф (необязательно)</div>
            <div style={{ position: 'relative' }}>
              <select value={form.tariff} onChange={e => set('tariff', e.target.value)} style={selStyle}>
                <option value="">— без тарифа —</option>
                {tariffs.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
              <ChevronDown size={13} style={{ position: 'absolute', right: 10, top: '50%',
                transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
            </div>
          </div>

          {/* Optional computer group (zone) — required when a tariff is set */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>
              Зал / зона{form.tariff ? ' *' : ' (необязательно)'}
            </div>
            <div style={{ position: 'relative' }}>
              <select value={form.computer_group} onChange={e => set('computer_group', e.target.value)} style={selStyle}>
                <option value="">— без зала —</option>
                {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
              <ChevronDown size={13} style={{ position: 'absolute', right: 10, top: '50%',
                transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
            </div>
          </div>

          {/* Component products with qty */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Товары в комбо</div>
              <button className="btn btn-secondary" onClick={addItem}
                style={{ fontSize: 11, padding: '4px 8px', gap: 4 }}>
                <Plus size={12} /> Добавить
              </button>
            </div>
            {items.length === 0 && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', padding: '6px 0' }}>Нет товаров</div>
            )}
            {items.map((it, idx) => (
              <div key={idx} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                <div style={{ position: 'relative', flex: 1 }}>
                  <select value={it.product} onChange={e => setItem(idx, 'product', e.target.value)} style={selStyle}>
                    <option value="">— выберите товар —</option>
                    {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <ChevronDown size={13} style={{ position: 'absolute', right: 10, top: '50%',
                    transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
                </div>
                <input type="number" min="1" step="1" value={it.qty}
                  onChange={e => setItem(idx, 'qty', e.target.value)}
                  style={{ ...iStyle, width: 64, textAlign: 'center', padding: '9px 6px' }} />
                <button className="icon-btn" style={{ color: '#ef4444', flexShrink: 0 }}
                  onClick={() => removeItem(idx)} title="Убрать"><Trash2 size={13} /></button>
              </div>
            ))}
          </div>

          {/* Toggles */}
          <div style={{ display: 'flex', gap: 20 }}>
            {[
              { label: 'Применять скидки клуба', key: 'applies_discount' },
              { label: 'Активен', key: 'is_active' },
            ].map(f => (
              <label key={f.key} style={{ display: 'flex', alignItems: 'center', gap: 8,
                cursor: 'pointer', fontSize: 13, color: 'var(--text-muted)' }}>
                <input type="checkbox" checked={!!form[f.key]}
                  onChange={e => set(f.key, e.target.checked)}
                  style={{ width: 16, height: 16, accentColor: 'var(--accent)' }} />
                {f.label}
              </label>
            ))}
          </div>
        </div>

        <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border-color)',
          display: 'flex', gap: 10, justifyContent: 'flex-end', flexShrink: 0 }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Отмена</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Сохранение…' : isEdit ? 'Сохранить' : 'Создать'}
          </button>
        </div>
      </div>
    </div>
  );
};

const Combos = () => {
  const { toast } = useToast();
  const clubId = localStorage.getItem('active_club_id');
  const [combos, setCombos] = useState([]);
  const [products, setProducts] = useState([]);
  const [tariffs, setTariffs] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState(null); // null=closed, {}=new, {...}=edit

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const club = clubId ? `club=${clubId}` : '';
      const [cb, pr, tf, gr] = await Promise.all([
        apiFetch(`/api/v1/shops/combos/?${club}&limit=500`).catch(() => []),
        apiFetch(`/api/v1/shops/admin/products/?${club}&limit=500`).catch(() => []),
        apiFetch(`/api/v1/billing/tariffs/?${club}&all=1&limit=500`).catch(() => []),
        apiFetch(`/api/v1/computers/groups/?${club}`).catch(() => []),
      ]);
      setCombos(cb.results || cb || []);
      setProducts(pr.results || pr || []);
      setTariffs(tf.results || tf || []);
      setGroups(gr.results || gr || []);
    } finally { setLoading(false); }
  }, [clubId]);

  useEffect(() => { load(); }, [load]);

  const remove = async (row) => {
    if (!window.confirm(`Удалить «${row.name}»?`)) return;
    try {
      await apiFetch(`/api/v1/shops/combos/${row.id}/`, { method: 'DELETE' });
      toast('Удалено', { type: 'success' });
      load();
    } catch (e) { toast(e.message || 'Ошибка удаления', { type: 'error' }); }
  };

  const filtered = search
    ? combos.filter(r => String(r.name || '').toLowerCase().includes(search.toLowerCase()))
    : combos;

  const th = {
    padding: '12px 14px', textAlign: 'left', fontWeight: 500, fontSize: 11,
    color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', whiteSpace: 'nowrap',
  };

  return (
    <div style={{ padding: '0 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0, display: 'inline-flex', alignItems: 'center', gap: 10 }}>
          <Layers size={20} /> Комбо-наборы
        </h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input type="text" placeholder="Поиск..." value={search} onChange={e => setSearch(e.target.value)}
              style={{ background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: 8,
                padding: '8px 12px 8px 32px', color: 'var(--text-light)', fontSize: 13, width: 220 }} />
          </div>
          <button className="btn btn-secondary" onClick={load} title="Обновить"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><RefreshCw size={14} /></button>
          <button className="btn btn-primary" onClick={() => setEditing({})}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}><Plus size={14} /> Создать</button>
        </div>
      </div>

      <div style={{ background: 'var(--bg-panel)', borderRadius: 12, border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              <th style={th}>Название</th>
              <th style={th}>Зал</th>
              <th style={th}>Тариф</th>
              <th style={th}>Товаров</th>
              <th style={th}>Цена</th>
              <th style={th}>Активен</th>
              <th style={{ ...th, textAlign: 'right' }}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={7} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Загрузка…</td></tr>}
            {!loading && filtered.length === 0 && <tr><td colSpan={7} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Записей нет</td></tr>}
            {filtered.map(row => (
              <tr key={row.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <td style={{ padding: '12px 14px', fontWeight: 600 }}>{row.name}</td>
                <td style={{ padding: '12px 14px' }}>{row.computer_group_name || '—'}</td>
                <td style={{ padding: '12px 14px' }}>{row.tariff_name || '—'}</td>
                <td style={{ padding: '12px 14px' }}>{(row.product_items || []).length} шт.</td>
                <td style={{ padding: '12px 14px', fontWeight: 600 }}>{fmtMoney(row.sale_price)}</td>
                <td style={{ padding: '12px 14px' }}>{row.is_active ? '✅' : '❌'}</td>
                <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                  <button className="icon-btn" onClick={() => setEditing(row)} title="Редактировать"><Edit2 size={14} /></button>
                  <button className="icon-btn" onClick={() => remove(row)} title="Удалить" style={{ color: '#ef4444', marginLeft: 4 }}><Trash2 size={14} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing !== null && (
        <ComboModal
          combo={editing?.id ? editing : null}
          products={products}
          tariffs={tariffs}
          groups={groups}
          clubId={clubId}
          onClose={() => setEditing(null)}
          onSaved={load}
        />
      )}
    </div>
  );
};

export default Combos;
