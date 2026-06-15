import { useState, useEffect, useCallback } from 'react';
import {
  Package, Plus, X, Search, RefreshCw,
  Download, Minus, Eye, EyeOff, Edit2, Trash2,
  ChevronDown, Send,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

const fmtMoney = (v) =>
  v == null ? '—' : Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' сум';

const fmtQty = (v) =>
  v == null ? '∞' : Number(v).toLocaleString('ru-RU') + ' шт.';

/* ─── Stock adjustment modal ─────────────────────────────────────────── */
const StockModal = ({ product, onClose, onSuccess }) => {
  const { toast } = useToast();
  const [delta, setDelta] = useState('');
  const [mode, setMode] = useState('add');
  const [loading, setLoading] = useState(false);
  const currentStock = product.current_stock ?? 0;

  const newQty = (() => {
    const val = parseInt(delta) || 0;
    if (mode === 'add') return currentStock + val;
    if (mode === 'remove') return Math.max(0, currentStock - val);
    return val;
  })();

  const handleSave = async () => {
    const val = parseInt(delta);
    if (!val || val <= 0) { toast('Введите количество', { type: 'warning' }); return; }
    const actualDelta = mode === 'remove' ? -val : mode === 'set' ? val - currentStock : val;
    if (actualDelta === 0) { onClose(); return; }
    setLoading(true);
    try {
      await apiFetch(`/api/v1/shops/admin/products/${product.id}/stock/`, {
        method: 'POST',
        body: JSON.stringify({ delta: actualDelta }),
      });
      const action = mode === 'add' ? `+${val}` : mode === 'remove' ? `−${val}` : `→ ${val}`;
      toast(`«${product.name}»: ${action} шт`, { type: 'success' });
      onSuccess();
      onClose();
    } catch (e) {
      toast(e.message || 'Ошибка', { type: 'error' });
    } finally { setLoading(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 14, padding: 24,
        width: 380, border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 15 }}>Управление остатком</h3>
          <button className="icon-btn" onClick={onClose}><X size={16} /></button>
        </div>
        <div style={{ padding: '10px 14px', background: 'rgba(255,255,255,0.04)',
          borderRadius: 10, marginBottom: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>{product.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Текущий: <strong style={{ color: currentStock > 0 ? '#10b981' : '#ef4444' }}>
              {currentStock} шт.
            </strong>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
          {[
            { id: 'add', label: '+ Приход', color: '#10b981' },
            { id: 'remove', label: '− Списание', color: '#ef4444' },
            { id: 'set', label: '= Установить', color: '#6366f1' },
          ].map(m => (
            <button key={m.id} onClick={() => setMode(m.id)}
              style={{ flex: 1, padding: '7px 4px', borderRadius: 8, fontSize: 11,
                fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit',
                background: mode === m.id ? m.color + '22' : 'rgba(255,255,255,0.04)',
                border: `1px solid ${mode === m.id ? m.color : 'var(--border-color)'}`,
                color: mode === m.id ? m.color : 'var(--text-muted)' }}>
              {m.label}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <button className="icon-btn" style={{ width: 36, height: 36, flexShrink: 0 }}
            onClick={() => setDelta(v => String(Math.max(1, (parseInt(v) || 0) - 1)))}>
            <Minus size={13} />
          </button>
          <input type="number" min="1" value={delta} placeholder="0"
            onChange={e => setDelta(e.target.value)}
            style={{ flex: 1, textAlign: 'center', height: 38, background: 'var(--bg-dark)',
              border: '1px solid var(--border-color)', borderRadius: 8,
              color: 'var(--text-main)', fontSize: 15, fontFamily: 'inherit', padding: '0 12px' }} />
          <button className="icon-btn" style={{ width: 36, height: 36, flexShrink: 0 }}
            onClick={() => setDelta(v => String((parseInt(v) || 0) + 1))}>
            <Plus size={13} />
          </button>
        </div>
        {delta && parseInt(delta) > 0 && (
          <div style={{ textAlign: 'center', marginBottom: 16, fontSize: 13, color: 'var(--text-muted)' }}>
            После изменения:{' '}
            <strong style={{ color: newQty > 0 ? '#10b981' : '#ef4444', fontSize: 16 }}>
              {newQty} шт.
            </strong>
          </div>
        )}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={loading}>Отмена</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={loading}>
            {loading ? 'Сохранение…' : 'Применить'}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Product form modal ─────────────────────────────────────────────── */
const ProductModal = ({ product, categories, clubId, onClose, onSaved }) => {
  const { toast } = useToast();
  const [form, setForm] = useState({
    name: product?.name || '',
    category: product?.category || '',
    price: product?.price || '',
    purchase_price: product?.purchase_price || '',
    original_price: product?.original_price || '',
    barcode: product?.barcode || '',
    description: product?.description || '',
    shell_display: product?.shell_display ?? true,
    is_active: product?.is_active ?? true,
  });
  const [quantity, setQuantity] = useState('');           // initial stock (create only)
  const [imageFile, setImageFile] = useState(null);       // chosen photo file
  const [imagePreview, setImagePreview] = useState(product?.main_image || null);
  const [saving, setSaving] = useState(false);
  const isEdit = !!product?.id;

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const onPickImage = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const handleSave = async () => {
    if (!form.name.trim()) { toast('Введите название', { type: 'warning' }); return; }
    if (!form.price) { toast('Введите цену продажи', { type: 'warning' }); return; }
    if (!form.category) { toast('Выберите категорию', { type: 'warning' }); return; }
    setSaving(true);
    try {
      const fields = {
        name: form.name.trim(),
        category: Number(form.category),
        price: Number(form.price),
        barcode: form.barcode || '',
        description: form.description || '',
        shell_display: !!form.shell_display,
        is_active: !!form.is_active,
        club: clubId ? Number(clubId) : null,
      };
      if (form.purchase_price) fields.purchase_price = Number(form.purchase_price);
      if (form.original_price) fields.original_price = Number(form.original_price);

      // If a photo file was picked, send multipart/form-data (main_image is an
      // ImageField) — apiFetch detects FormData and sets the right headers.
      let opts;
      if (imageFile) {
        const fd = new FormData();
        Object.entries(fields).forEach(([k, v]) => {
          if (v === null || v === undefined) return;
          fd.append(k, typeof v === 'boolean' ? (v ? 'true' : 'false') : String(v));
        });
        fd.append('main_image', imageFile);
        opts = { body: fd };
      } else {
        opts = { body: JSON.stringify(fields) };
      }

      if (isEdit) {
        await apiFetch(`/api/v1/shops/admin/products/${product.id}/`, { method: 'PATCH', ...opts });
        toast('Товар обновлён', { type: 'success' });
      } else {
        const saved = await apiFetch('/api/v1/shops/admin/products/', { method: 'POST', ...opts });
        // Set the initial stock quantity for the freshly-created product.
        const qty = parseInt(quantity) || 0;
        if (qty > 0 && saved?.id) {
          try {
            await apiFetch(`/api/v1/shops/admin/products/${saved.id}/stock/`, {
              method: 'POST', body: JSON.stringify({ delta: qty }),
            });
          } catch { /* product created; stock can still be set via «Остаток» */ }
        }
        toast('Товар добавлен', { type: 'success' });
      }
      onSaved();
      onClose();
    } catch (e) {
      toast(e.message || 'Ошибка сохранения', { type: 'error' });
    } finally { setSaving(false); }
  };

  const iStyle = {
    width: '100%', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
    borderRadius: 8, padding: '9px 12px', color: 'var(--text-main)',
    fontSize: 13, fontFamily: 'inherit', boxSizing: 'border-box',
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 14, width: 480,
        maxHeight: '90vh', display: 'flex', flexDirection: 'column',
        border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        {/* Header */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-color)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
          <h3 style={{ margin: 0, fontSize: 15 }}>{isEdit ? 'Редактировать товар' : 'Добавить товар'}</h3>
          <button className="icon-btn" onClick={onClose}><X size={15} /></button>
        </div>
        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '18px 20px' }}>
          {[
            { label: 'Название *', key: 'name', type: 'text', placeholder: 'Cola 0.5л' },
            { label: 'Штрихкод', key: 'barcode', type: 'text', placeholder: '4600591026' },
          ].map(f => (
            <div key={f.key} style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{f.label}</div>
              <input type={f.type} value={form[f.key]} placeholder={f.placeholder}
                onChange={e => set(f.key, e.target.value)} style={iStyle} />
            </div>
          ))}

          {/* Category */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Категория *</div>
            <div style={{ position: 'relative' }}>
              <select value={form.category} onChange={e => set('category', e.target.value)}
                style={{ ...iStyle, appearance: 'none', paddingRight: 28, cursor: 'pointer' }}>
                <option value="">— выберите —</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <ChevronDown size={13} style={{ position: 'absolute', right: 10, top: '50%',
                transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
            </div>
          </div>

          {/* Prices */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 14 }}>
            {[
              { label: 'Цена продажи сум *', key: 'price' },
              { label: 'Цена закупки сум', key: 'purchase_price' },
              { label: 'Старая цена сум', key: 'original_price' },
            ].map(f => (
              <div key={f.key}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 3 }}>{f.label}</div>
                <input type="number" min="0" step="0.01" value={form[f.key]}
                  onChange={e => set(f.key, e.target.value)} placeholder="0"
                  style={{ ...iStyle, padding: '9px 8px' }} />
              </div>
            ))}
          </div>

          {/* Initial quantity (only for a new product; afterwards use «Остаток») */}
          {!isEdit && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Количество (шт)</div>
              <input type="number" min="0" step="1" value={quantity}
                onChange={e => setQuantity(e.target.value)} placeholder="0" style={iStyle} />
            </div>
          )}

          {/* Photo — upload from computer (no URL needed) */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Фото товара</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {imagePreview && (
                <img src={imagePreview} alt="" style={{ width: 48, height: 48, borderRadius: 8,
                  objectFit: 'cover', border: '1px solid var(--border-color)', flexShrink: 0 }} />
              )}
              <label className="btn btn-secondary" style={{ cursor: 'pointer', fontSize: 12, margin: 0 }}>
                {imageFile ? '✓ Файл выбран' : '📁 Загрузить с компьютера'}
                <input type="file" accept="image/*" onChange={onPickImage} style={{ display: 'none' }} />
              </label>
            </div>
          </div>

          {/* Description */}
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Описание</div>
            <textarea value={form.description} onChange={e => set('description', e.target.value)}
              rows={2} style={{ ...iStyle, resize: 'vertical', minHeight: 56 }} />
          </div>

          {/* Toggles */}
          <div style={{ display: 'flex', gap: 20 }}>
            {[
              { label: 'Показывать в шелле', key: 'shell_display' },
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
        {/* Footer */}
        <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border-color)',
          display: 'flex', gap: 10, justifyContent: 'flex-end', flexShrink: 0 }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Отмена</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Сохранение…' : isEdit ? 'Сохранить' : 'Добавить'}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Category (group) form modal ───────────────────────────────────── */
const CategoryModal = ({ category, onClose, onSaved }) => {
  const { toast } = useToast();
  const [name, setName] = useState(category?.name || '');
  const [saving, setSaving] = useState(false);
  const isEdit = !!category?.id;

  const handleSave = async () => {
    if (!name.trim()) { toast('Введите название', { type: 'warning' }); return; }
    setSaving(true);
    try {
      const slug = name.toLowerCase().replace(/[^a-zа-яё0-9]+/gi, '-').slice(0, 50);
      if (isEdit) {
        await apiFetch(`/api/v1/shops/categories/${category.slug}/update/`, {
          method: 'PATCH', body: JSON.stringify({ name }),
        });
        toast('Группа обновлена', { type: 'success' });
      } else {
        await apiFetch('/api/v1/shops/categories/create/', {
          method: 'POST', body: JSON.stringify({ name, slug }),
        });
        toast('Группа добавлена', { type: 'success' });
      }
      onSaved();
      onClose();
    } catch (e) {
      toast(e.message || 'Ошибка', { type: 'error' });
    } finally { setSaving(false); }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 900 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background: 'var(--bg-panel)', borderRadius: 14, padding: 24,
        width: 380, border: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 15 }}>{isEdit ? 'Редактировать группу' : 'Добавить группу'}</h3>
          <button className="icon-btn" onClick={onClose}><X size={15} /></button>
        </div>
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>Название *</div>
          <input value={name} onChange={e => setName(e.target.value)}
            placeholder="Например: Напитки"
            onKeyDown={e => e.key === 'Enter' && handleSave()}
            style={{ width: '100%', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
              borderRadius: 8, padding: '10px 12px', color: 'var(--text-main)',
              fontSize: 13, fontFamily: 'inherit', boxSizing: 'border-box' }} />
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={saving}>Отмена</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Сохранение…' : isEdit ? 'Сохранить' : 'Добавить'}
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Export CSV helper ──────────────────────────────────────────────── */
const exportCSV = (products, categories) => {
  const catMap = Object.fromEntries(categories.map(c => [c.id, c.name]));
  const rows = [
    ['Название', 'Категория', 'Цена продажи', 'Цена закупки', 'Остаток', 'Стоимость остатков', 'В шелле', 'Активен'],
    ...products.map(p => [
      p.name,
      catMap[p.category] || '—',
      p.price || 0,
      p.purchase_price || 0,
      p.current_stock ?? 0,
      ((p.current_stock ?? 0) * (p.purchase_price || 0)).toFixed(0),
      p.shell_display ? 'Да' : 'Нет',
      p.is_active ? 'Да' : 'Нет',
    ]),
  ];
  const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'products.csv'; a.click();
  URL.revokeObjectURL(url);
};

/* ─── Badge components ───────────────────────────────────────────────── */
const DiscountBadge = ({ product }) => {
  const hasDiscount = product.original_price && Number(product.original_price) > Number(product.price);
  return (
    <span style={{
      fontSize: 11, padding: '3px 8px', borderRadius: 999, fontWeight: 500,
      background: hasDiscount ? 'rgba(16,185,129,0.1)' : 'rgba(255,255,255,0.05)',
      color: hasDiscount ? '#10b981' : 'var(--text-muted)',
      border: `1px solid ${hasDiscount ? 'rgba(16,185,129,0.25)' : 'rgba(255,255,255,0.08)'}`,
    }}>
      {hasDiscount ? 'Применяется' : 'Не применяется'}
    </span>
  );
};

const StockBadge = ({ qty }) => {
  const n = qty ?? 0;
  const color = n > 5 ? '#10b981' : n > 0 ? '#f59e0b' : '#ef4444';
  return (
    <span style={{ fontWeight: 600, color, fontSize: 13 }}>
      {fmtQty(qty)}
    </span>
  );
};

/* ─── Main Products page ─────────────────────────────────────────────── */
const Products = () => {
  const { toast } = useToast();
  const clubId = localStorage.getItem('active_club_id');

  const [tab, setTab] = useState('products');   // 'products' | 'groups'
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterCat, setFilterCat] = useState('');  // category id filter

  const [stockProduct, setStockProduct] = useState(null);
  const [editProduct, setEditProduct] = useState(null);   // null=closed, {}=new, {...}=edit
  const [editCategory, setEditCategory] = useState(null); // null=closed, {}=new, {...}=edit
  const [selected, setSelected] = useState(new Set());

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = clubId
        ? `/api/v1/shops/admin/products/?club=${clubId}`
        : '/api/v1/shops/admin/products/';
      const [prods, cats] = await Promise.all([
        apiFetch(url).catch(() => []),
        apiFetch('/api/v1/shops/categories/').catch(() => []),
      ]);
      setProducts(prods.results || prods || []);
      setCategories(cats.results || cats || []);
    } finally { setLoading(false); }
  }, [clubId]);

  useEffect(() => { load(); }, [load]);

  /* ── derived data ── */
  const catMap = Object.fromEntries(categories.map(c => [c.id, c.name]));

  const filtered = products.filter(p => {
    const matchSearch = !search || p.name.toLowerCase().includes(search.toLowerCase());
    const matchCat = !filterCat || String(p.category) === String(filterCat);
    return matchSearch && matchCat;
  });

  const totalStockValue = products.reduce((s, p) =>
    s + (p.current_stock ?? 0) * (p.purchase_price || 0), 0);

  /* ── select all ── */
  const allIds = filtered.map(p => p.id);
  const allSelected = allIds.length > 0 && allIds.every(id => selected.has(id));
  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(allIds));
  };
  const toggleOne = (id) => {
    const s = new Set(selected);
    if (s.has(id)) s.delete(id); else s.add(id);
    setSelected(s);
  };

  /* ── delete product ── */
  const deleteProduct = async (p) => {
    if (!window.confirm(`Удалить «${p.name}»?`)) return;
    try {
      await apiFetch(`/api/v1/shops/admin/products/${p.id}/`, { method: 'DELETE' });
      toast(`«${p.name}» удалён`, { type: 'success' });
      load();
    } catch (e) { toast(e.message || 'Ошибка', { type: 'error' }); }
  };

  /* ── toggle shell display ── */
  const toggleShellDisplay = async (p) => {
    try {
      await apiFetch(`/api/v1/shops/admin/products/${p.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ shell_display: !p.shell_display }),
      });
      setProducts(prev => prev.map(x => x.id === p.id ? { ...x, shell_display: !x.shell_display } : x));
    } catch (e) { toast(e.message || 'Ошибка', { type: 'error' }); }
  };

  /* ── delete category ── */
  const deleteCategory = async (cat) => {
    if (!window.confirm(`Удалить группу «${cat.name}»?`)) return;
    try {
      await apiFetch(`/api/v1/shops/categories/${cat.slug}/delete/`, { method: 'DELETE' });
      toast(`«${cat.name}» удалена`, { type: 'success' });
      load();
    } catch (e) { toast(e.message || 'Ошибка', { type: 'error' }); }
  };

  /* ── column header style ── */
  const th = {
    padding: '10px 12px', textAlign: 'left', fontSize: 10,
    color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase',
    letterSpacing: '0.5px', whiteSpace: 'nowrap', userSelect: 'none',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>

      {/* ── Top bar ── */}
      <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-color)',
        flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {/* Tabs */}
          <button onClick={() => setTab('products')}
            style={{ padding: '7px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
              cursor: 'pointer', fontFamily: 'inherit', border: 'none',
              background: tab === 'products' ? 'var(--accent)' : 'transparent',
              color: tab === 'products' ? '#fff' : 'var(--text-muted)' }}>
            Товары {products.length}
          </button>
          <button onClick={() => setTab('groups')}
            style={{ padding: '7px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
              cursor: 'pointer', fontFamily: 'inherit', border: 'none',
              background: tab === 'groups' ? 'var(--accent)' : 'transparent',
              color: tab === 'groups' ? '#fff' : 'var(--text-muted)' }}>
            Группы {categories.length}
          </button>
        </div>

        {tab === 'products' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Search */}
            <div style={{ position: 'relative' }}>
              <Search size={13} style={{ position: 'absolute', left: 10, top: '50%',
                transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }} />
              <input value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Поиск по товарам"
                style={{ height: 36, paddingLeft: 32, paddingRight: 10, width: 220,
                  background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                  borderRadius: 8, color: 'var(--text-main)', fontSize: 13, fontFamily: 'inherit' }} />
            </div>

            {/* Category filter */}
            <div style={{ position: 'relative' }}>
              <select value={filterCat} onChange={e => setFilterCat(e.target.value)}
                style={{ height: 36, paddingLeft: 10, paddingRight: 28, minWidth: 140,
                  background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                  borderRadius: 8, color: filterCat ? 'var(--text-main)' : 'var(--text-muted)',
                  fontSize: 13, fontFamily: 'inherit', appearance: 'none', cursor: 'pointer' }}>
                <option value="">Все группы</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <ChevronDown size={12} style={{ position: 'absolute', right: 9, top: '50%',
                transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-muted)' }} />
            </div>

            {/* Stock total */}
            <div style={{ padding: '0 14px', height: 36, background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border-color)', borderRadius: 8, display: 'flex',
              alignItems: 'center', fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
              Сумма остатков:&nbsp;
              <strong style={{ color: 'var(--text-main)' }}>{fmtMoney(totalStockValue)}</strong>
            </div>

            {/* Refresh */}
            <button className="icon-btn" onClick={load} disabled={loading} title="Обновить">
              <RefreshCw size={14} />
            </button>

            {/* Export CSV */}
            <button className="btn btn-secondary"
              onClick={() => exportCSV(products, categories)}
              style={{ height: 36, padding: '0 14px', fontSize: 12, gap: 6 }}>
              <Download size={13} /> Экспорт в .CSV
            </button>

            {/* Add product */}
            <button className="btn btn-primary"
              onClick={() => setEditProduct({})}
              style={{ height: 36, padding: '0 14px', fontSize: 12, gap: 6 }}>
              <Plus size={13} /> Добавить товар
            </button>
          </div>
        )}

        {tab === 'groups' && (
          <div style={{ display: 'flex', gap: 10 }}>
            <button className="icon-btn" onClick={load} disabled={loading} title="Обновить">
              <RefreshCw size={14} />
            </button>
            <button className="btn btn-primary"
              onClick={() => setEditCategory({})}
              style={{ height: 36, padding: '0 14px', fontSize: 12, gap: 6 }}>
              <Plus size={13} /> Добавить группу
            </button>
          </div>
        )}
      </div>

      {/* ── Content ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px' }}>

        {/* ── PRODUCTS TAB ── */}
        {tab === 'products' && (
          loading ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
              Загрузка…
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)',
              background: 'var(--bg-panel)', borderRadius: 12, border: '1px solid var(--border-color)' }}>
              <Package size={32} style={{ opacity: 0.25, marginBottom: 12 }} />
              <div style={{ fontSize: 14 }}>Нет товаров</div>
              {!clubId && (
                <div style={{ fontSize: 12, marginTop: 6 }}>Выберите клуб для отображения товаров</div>
              )}
            </div>
          ) : (
            <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
              borderRadius: 12, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-dark)' }}>
                    <th style={{ ...th, width: 36, padding: '10px 10px 10px 14px' }}>
                      <input type="checkbox" checked={allSelected} onChange={toggleAll}
                        style={{ width: 15, height: 15, accentColor: 'var(--accent)', cursor: 'pointer' }} />
                    </th>
                    <th style={{ ...th, width: 48 }}></th>
                    <th style={th}>Название</th>
                    <th style={th}>Группа</th>
                    <th style={th}>Скидка</th>
                    <th style={th}>Остаток</th>
                    <th style={th}>Цена закупки</th>
                    <th style={th}>Цена продажи</th>
                    <th style={th}>Стоимость остатков</th>
                    <th style={{ ...th, textAlign: 'center' }}>Отображение</th>
                    <th style={{ ...th, width: 60 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(p => {
                    const stockValue = (p.current_stock ?? 0) * (p.purchase_price || 0);
                    const catName = catMap[p.category] || null;
                    return (
                      <tr key={p.id}
                        style={{ borderBottom: '1px solid var(--border-row)',
                          background: selected.has(p.id) ? 'rgba(99,102,241,0.04)' : 'transparent',
                          opacity: p.is_active ? 1 : 0.5 }}
                        onMouseEnter={e => { if (!selected.has(p.id)) e.currentTarget.style.background = 'var(--hover-overlay)'; }}
                        onMouseLeave={e => { if (!selected.has(p.id)) e.currentTarget.style.background = 'transparent'; }}>

                        {/* Checkbox */}
                        <td style={{ padding: '10px 10px 10px 14px' }}>
                          <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggleOne(p.id)}
                            style={{ width: 15, height: 15, accentColor: 'var(--accent)', cursor: 'pointer' }} />
                        </td>

                        {/* Image */}
                        <td style={{ padding: '8px 8px' }}>
                          <img
                            src={p.main_image || `https://picsum.photos/seed/p${p.id}/60/60`}
                            alt=""
                            onError={e => { e.target.src = `https://picsum.photos/seed/p${p.id}/60/60`; }}
                            style={{ width: 40, height: 40, borderRadius: 6, objectFit: 'cover', display: 'block' }} />
                        </td>

                        {/* Name */}
                        <td style={{ padding: '10px 12px', fontWeight: 600, maxWidth: 200 }}>
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {p.name}
                          </div>
                        </td>

                        {/* Category */}
                        <td style={{ padding: '10px 12px' }}>
                          {catName ? (
                            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999,
                              background: 'rgba(99,102,241,0.1)', color: 'var(--accent)',
                              fontWeight: 500, whiteSpace: 'nowrap' }}>
                              {catName}
                            </span>
                          ) : <span style={{ color: 'var(--text-muted)' }}>Без группы</span>}
                        </td>

                        {/* Discount badge */}
                        <td style={{ padding: '10px 12px' }}>
                          <DiscountBadge product={p} />
                        </td>

                        {/* Stock */}
                        <td style={{ padding: '10px 12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <StockBadge qty={p.current_stock} />
                            <button onClick={() => setStockProduct(p)}
                              style={{ width: 20, height: 20, borderRadius: 4, border: 'none',
                                background: 'rgba(99,102,241,0.1)', color: 'var(--accent)',
                                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                opacity: 0.6, flexShrink: 0 }}
                              title="Изменить остаток">
                              <Send size={10} />
                            </button>
                          </div>
                        </td>

                        {/* Purchase price */}
                        <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                          {p.purchase_price ? fmtMoney(p.purchase_price) : '—'}
                        </td>

                        {/* Sale price */}
                        <td style={{ padding: '10px 12px', fontWeight: 700 }}>
                          {fmtMoney(p.price)}
                        </td>

                        {/* Stock value */}
                        <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>
                          {p.purchase_price ? fmtMoney(stockValue) : '—'}
                        </td>

                        {/* Shell display toggle */}
                        <td style={{ padding: '10px 12px', textAlign: 'center' }}>
                          <button onClick={() => toggleShellDisplay(p)}
                            title={p.shell_display ? 'Скрыть из шелла' : 'Показать в шелле'}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4,
                              color: p.shell_display ? 'var(--accent)' : 'var(--text-muted)',
                              display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                            {p.shell_display ? <Eye size={16} /> : <EyeOff size={16} />}
                          </button>
                        </td>

                        {/* Actions */}
                        <td style={{ padding: '10px 10px' }}>
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button className="icon-btn" style={{ width: 26, height: 26 }}
                              title="Редактировать"
                              onClick={() => setEditProduct(p)}>
                              <Edit2 size={12} />
                            </button>
                            <button className="icon-btn" style={{ width: 26, height: 26,
                              color: '#ef4444' }}
                              title="Удалить"
                              onClick={() => deleteProduct(p)}>
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )
        )}

        {/* ── GROUPS TAB ── */}
        {tab === 'groups' && (
          loading ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Загрузка…</div>
          ) : categories.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)',
              background: 'var(--bg-panel)', borderRadius: 12, border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: 14 }}>Нет групп</div>
              <div style={{ fontSize: 12, marginTop: 6 }}>Создайте группу товаров</div>
            </div>
          ) : (
            <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
              borderRadius: 12, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-dark)' }}>
                    <th style={th}>Название группы</th>
                    <th style={th}>Slug</th>
                    <th style={{ ...th, textAlign: 'right' }}>Товаров</th>
                    <th style={{ ...th, width: 80 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map(cat => {
                    const count = products.filter(p => String(p.category) === String(cat.id)).length;
                    return (
                      <tr key={cat.id}
                        style={{ borderBottom: '1px solid var(--border-row)' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <td style={{ padding: '12px 14px', fontWeight: 600 }}>
                          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 999, marginRight: 8,
                            background: 'rgba(99,102,241,0.1)', color: 'var(--accent)', fontWeight: 500 }}>
                            {cat.name}
                          </span>
                        </td>
                        <td style={{ padding: '12px 14px', color: 'var(--text-muted)', fontSize: 12, fontFamily: 'monospace' }}>
                          {cat.slug}
                        </td>
                        <td style={{ padding: '12px 14px', textAlign: 'right', fontWeight: 600 }}>
                          {count} шт.
                        </td>
                        <td style={{ padding: '12px 10px' }}>
                          <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                            <button className="icon-btn" style={{ width: 26, height: 26 }}
                              title="Редактировать"
                              onClick={() => setEditCategory(cat)}>
                              <Edit2 size={12} />
                            </button>
                            <button className="icon-btn" style={{ width: 26, height: 26, color: '#ef4444' }}
                              title="Удалить"
                              onClick={() => deleteCategory(cat)}>
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>

      {/* ── Modals ── */}
      {stockProduct && (
        <StockModal
          product={stockProduct}
          onClose={() => setStockProduct(null)}
          onSuccess={load}
        />
      )}
      {editProduct !== null && (
        <ProductModal
          product={editProduct?.id ? editProduct : null}
          categories={categories}
          clubId={clubId}
          onClose={() => setEditProduct(null)}
          onSaved={load}
        />
      )}
      {editCategory !== null && (
        <CategoryModal
          category={editCategory?.id ? editCategory : null}
          onClose={() => setEditCategory(null)}
          onSaved={load}
        />
      )}
    </div>
  );
};

export default Products;
