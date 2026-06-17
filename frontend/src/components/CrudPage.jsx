import { useState, useEffect, useCallback } from 'react';
import { Plus, Edit2, Trash2, X as XIcon, Search, RefreshCw } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from './Toast';

/**
 * Universal CRUD list+form page.
 *
 * Props:
 *   title          - page title (e.g. "Скидки")
 *   icon           - lucide icon component
 *   endpoint       - REST endpoint root (e.g. "/api/v1/loyalty/discounts/")
 *   columns        - array of {key, label, render?(row)}
 *   formFields     - array of {name, label, type, placeholder?, options?, required?, defaultValue?, hint?}
 *   searchField    - field name to filter by (client-side)
 *   tenantParam    - if true, append ?club=<id> on list and inject club in POST body
 */
const CrudPage = ({ title, icon: Icon, endpoint, columns, formFields, searchField = 'name', tenantParam = true }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [editing, setEditing] = useState(null); // null=no modal, {}=create, {id,...}=edit
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  const clubId = localStorage.getItem('active_club_id');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // limit=500 overrides the backend default LimitOffsetPagination cap
      // (PAGE_SIZE=20) so the whole list loads — search/filter is client-side
      // over the full set. The backend honors `limit`, not `page_size`.
      const url = tenantParam && clubId
        ? `${endpoint}?club=${clubId}&limit=500`
        : `${endpoint}?limit=500`;
      const json = await apiFetch(url);
      setItems(json.results || json || []);
    } catch (e) {
      console.error(`Load ${endpoint}`, e);
    } finally {
      setLoading(false);
    }
  }, [endpoint, clubId, tenantParam]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    const initial = { };
    formFields.forEach(f => { initial[f.name] = f.defaultValue ?? ''; });
    if (tenantParam && clubId) initial.club = Number(clubId);
    setForm(initial);
    setEditing({});
  };

  const openEdit = (row) => {
    const initial = { ...row };
    setForm(initial);
    setEditing(row);
  };

  const close = () => { setEditing(null); setForm({}); };

  const save = async () => {
    setSaving(true);
    try {
      const isCreate = !editing?.id;
      // Drop empty-string optional fields: the backend 400s on '' for
      // date/datetime (and other typed) fields, which blocked create. Required
      // fields are kept so the backend can report the missing-value error.
      const requiredNames = new Set(formFields.filter(f => f.required).map(f => f.name));
      const payload = {};
      Object.entries(form).forEach(([k, v]) => {
        if (v === '' && !requiredNames.has(k)) return;
        payload[k] = v;
      });
      const body = JSON.stringify(payload);
      if (isCreate) {
        await apiFetch(endpoint, { method: 'POST', body });
      } else {
        await apiFetch(`${endpoint}${editing.id}/`, { method: 'PATCH', body });
      }
      close();
      load();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка сохранения', { type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (row) => {
    if (!window.confirm(`Удалить «${row.name || row.code || row.title || row.id}»?`)) return;
    try {
      await apiFetch(`${endpoint}${row.id}/`, { method: 'DELETE' });
      toast('Удалено', { type: 'success' });
      load();
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка удаления', { type: 'error' });
    }
  };

  const filtered = search
    ? items.filter(r => String(r[searchField] || '').toLowerCase().includes(search.toLowerCase()))
    : items;

  return (
    <div style={{ padding: '0 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 600, margin: 0, display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
          {Icon && <Icon size={20} />} {title}
        </h2>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Поиск..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                borderRadius: '8px', padding: '8px 12px 8px 32px',
                color: 'var(--text-light)', fontSize: '13px', width: '220px',
              }}
            />
          </div>
          <button className="btn btn-secondary" onClick={load} title="Обновить"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <RefreshCw size={14} />
          </button>
          <button className="btn btn-primary" onClick={openCreate}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={14} /> Создать
          </button>
        </div>
      </div>

      <div style={{ background: 'var(--bg-panel)', borderRadius: '12px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
              {columns.map(col => (
                <th key={col.key} style={{
                  padding: '12px 14px', textAlign: 'left', fontWeight: 500, fontSize: '11px',
                  color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px',
                  whiteSpace: 'nowrap',
                }}>{col.label}</th>
              ))}
              <th style={{ padding: '12px 14px', textAlign: 'right', fontSize: '11px', color: 'var(--text-muted)' }}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={columns.length + 1} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Загрузка…</td></tr>
            )}
            {!loading && filtered.length === 0 && (
              <tr><td colSpan={columns.length + 1} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>Записей нет</td></tr>
            )}
            {filtered.map(row => (
              <tr key={row.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                {columns.map(col => (
                  <td key={col.key} style={{ padding: '12px 14px', verticalAlign: 'middle' }}>
                    {col.render ? col.render(row) : (row[col.key] != null ? String(row[col.key]) : '—')}
                  </td>
                ))}
                <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                  <button className="icon-btn" onClick={() => openEdit(row)} title="Редактировать">
                    <Edit2 size={14} />
                  </button>
                  <button className="icon-btn" onClick={() => remove(row)} title="Удалить" style={{ color: '#ef4444', marginLeft: '4px' }}>
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <div
          onClick={(e) => { if (e.target === e.currentTarget) close(); }}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 800,
          }}
        >
          <div style={{
            background: 'var(--bg-panel)', borderRadius: '14px',
            padding: '24px', width: '480px', maxWidth: '90vw',
            border: '1px solid var(--border-color)',
            maxHeight: '90vh', overflow: 'auto',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0 }}>{editing.id ? `Редактирование` : `Создать`}</h3>
              <button className="icon-btn" onClick={close}><XIcon size={16} /></button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {formFields.map(field => (
                <div key={field.name}>
                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                    {field.label}{field.required && ' *'}
                  </label>
                  {field.type === 'select' ? (
                    <select
                      value={form[field.name] ?? ''}
                      onChange={(e) => setForm(f => ({ ...f, [field.name]: e.target.value }))}
                      style={{
                        width: '100%', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                        borderRadius: '8px', padding: '10px 12px', color: 'var(--text-light)', fontSize: '13px',
                      }}
                    >
                      {field.options.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  ) : field.type === 'textarea' ? (
                    <textarea
                      value={form[field.name] ?? ''}
                      onChange={(e) => setForm(f => ({ ...f, [field.name]: e.target.value }))}
                      placeholder={field.placeholder}
                      rows={3}
                      style={{
                        width: '100%', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                        borderRadius: '8px', padding: '10px 12px', color: 'var(--text-light)', fontSize: '13px',
                        fontFamily: 'inherit', resize: 'vertical',
                      }}
                    />
                  ) : field.type === 'checkbox' ? (
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={!!form[field.name]}
                        onChange={(e) => setForm(f => ({ ...f, [field.name]: e.target.checked }))}
                      />
                      <span style={{ fontSize: '13px' }}>{field.hint || 'Включено'}</span>
                    </label>
                  ) : (
                    <input
                      type={field.type || 'text'}
                      value={form[field.name] ?? ''}
                      onChange={(e) => setForm(f => ({
                        ...f,
                        [field.name]: field.type === 'number' ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value,
                      }))}
                      placeholder={field.placeholder}
                      style={{
                        width: '100%', background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                        borderRadius: '8px', padding: '10px 12px', color: 'var(--text-light)', fontSize: '13px',
                      }}
                    />
                  )}
                  {field.hint && field.type !== 'checkbox' && (
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>{field.hint}</div>
                  )}
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '24px' }}>
              <button className="btn btn-secondary" onClick={close} disabled={saving}>Отмена</button>
              <button className="btn btn-primary" onClick={save} disabled={saving}>
                {saving ? 'Сохранение...' : (editing.id ? 'Сохранить' : 'Создать')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CrudPage;
