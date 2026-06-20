import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Plus, ChevronDown, ChevronUp, Edit2, Trash2, X,
  Image as ImageIcon, Eye, ToggleLeft, ToggleRight,
  Calendar, Link2, Newspaper, RefreshCw, Bold, Italic,
  List,
} from 'lucide-react';
import { apiFetch } from '../../api/client';
import { useToast } from '../../components/Toast';

/* ─── helpers ─────────────────────────────────────────────────────────── */
const fmtDate = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }); }
  catch { return '—'; }
};
const fmtDateTime = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return '—'; }
};
const toDateInput = (iso) => {
  if (!iso) return '';
  try {
    // BUGFIX: a datetime-local input expects LOCAL wall-clock time. Using
    // toISOString() here returned UTC, then save re-parsed that string as local
    // and shifted it again (double timezone drift). Build a local-time string so
    // the input ↔ save round-trip is consistent.
    const d = new Date(iso);
    const off = d.getTimezoneOffset() * 60000;
    return new Date(d.getTime() - off).toISOString().slice(0, 16);
  }
  catch { return ''; }
};

/* ─── Toggle switch ───────────────────────────────────────────────────── */
const Toggle = ({ value, onChange, label }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0' }}>
    {label && <span style={{ fontSize: '13px' }}>{label}</span>}
    <button onClick={() => onChange(!value)}
      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, display: 'flex' }}>
      {value
        ? <ToggleRight size={28} color="var(--accent)" />
        : <ToggleLeft size={28} color="var(--text-muted)" />}
    </button>
  </div>
);

/* ─── Input style ─────────────────────────────────────────────────────── */
const iStyle = {
  height: 38, padding: '0 12px', width: '100%', boxSizing: 'border-box',
  background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
  borderRadius: 8, color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit',
};

/* ─── News Preview card ───────────────────────────────────────────────── */
const NewsPreview = ({ title, body, buttonText, coverUrl, clubName }) => (
  <div style={{ background: '#18181b', borderRadius: 14, overflow: 'hidden',
    border: '1px solid rgba(255,255,255,0.08)', maxWidth: 260 }}>
    {coverUrl && (
      <img src={coverUrl} alt="" style={{ width: '100%', aspectRatio: '16/9', objectFit: 'cover', display: 'block' }} />
    )}
    {!coverUrl && (
      <div style={{ width: '100%', aspectRatio: '16/9', background: 'rgba(255,255,255,0.04)',
        display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <ImageIcon size={32} style={{ opacity: 0.2 }} />
      </div>
    )}
    <div style={{ padding: '12px 14px' }}>
      <div style={{ fontSize: '13px', fontWeight: 700, marginBottom: 6, color: '#fff',
        overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
        {title || 'Заголовок новости'}
      </div>
      <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.55)', lineHeight: 1.5,
        overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 4, WebkitBoxOrient: 'vertical' }}>
        {body || 'Текст новости будет отображаться здесь...'}
      </div>
      {buttonText && (
        <div style={{ marginTop: 10, padding: '7px 14px', background: 'var(--accent)',
          borderRadius: 8, fontSize: '12px', fontWeight: 600, color: '#fff', textAlign: 'center' }}>
          {buttonText}
        </div>
      )}
      {clubName && (
        <div style={{ marginTop: 8, fontSize: '10px', color: 'rgba(255,255,255,0.35)' }}>
          {clubName}
        </div>
      )}
    </div>
  </div>
);

/* ─── Create / Edit form panel ────────────────────────────────────────── */
const NewsForm = ({ item, clubId, onClose, onSaved }) => {
  const { toast } = useToast();
  const fileRef = useRef();
  const bodyRef = useRef();

  const [title, setTitle]           = useState(item?.title || '');
  const [body, setBody]             = useState(item?.body || '');
  const [btnText, setBtnText]       = useState(item?.button_text || '');
  const [btnUrl, setBtnUrl]         = useState(item?.button_url || '');
  const [btnEnabled, setBtnEnabled] = useState(!!(item?.button_text));
  const [published, setPublished]   = useState(item?.is_published ?? false);
  const [periodEnabled, setPeriodEnabled] = useState(!!(item?.show_from || item?.show_until));
  const [showFrom, setShowFrom]     = useState(toDateInput(item?.show_from));
  const [showUntil, setShowUntil]   = useState(toDateInput(item?.show_until));
  const [coverFile, setCoverFile]   = useState(null);
  const [coverPreview, setCoverPreview] = useState(item?.cover_image_url || null);
  const [saving, setSaving]         = useState(false);

  // BUGFIX: track the blob URL we create for the cover preview so it can be
  // revoked when replaced or on unmount (previously leaked an object URL each pick).
  const blobUrlRef = useRef(null);
  useEffect(() => () => {
    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
  }, []);

  /* format helpers for body textarea */
  const wrapSelection = (tag) => {
    const ta = bodyRef.current;
    if (!ta) return;
    const start = ta.selectionStart, end = ta.selectionEnd;
    const sel = ta.value.slice(start, end);
    if (!sel) return;
    const wrapped = `<${tag}>${sel}</${tag}>`;
    const newVal = ta.value.slice(0, start) + wrapped + ta.value.slice(end);
    setBody(newVal);
    setTimeout(() => {
      ta.focus();
      ta.setSelectionRange(start + tag.length + 2, start + tag.length + 2 + sel.length);
    }, 0);
  };

  const onFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 640 * 1024) { toast('Файл > 640 КБ', { type: 'warning' }); return; }
    setCoverFile(file);
    // Revoke any previously created blob URL before replacing the preview.
    if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    const url = URL.createObjectURL(file);
    blobUrlRef.current = url;
    setCoverPreview(url);
  };

  const save = async () => {
    if (!title.trim()) { toast('Введите заголовок', { type: 'warning' }); return; }
    setSaving(true);
    try {
      const fd = new FormData();
      fd.append('club', clubId);
      fd.append('title', title.trim());
      fd.append('body', body);
      fd.append('button_text', btnEnabled ? btnText : '');
      // BUGFIX: when the button is disabled, button_text was cleared but button_url
      // was omitted from the payload — leaving a stale URL in the DB on PATCH.
      // Always send button_url so it is cleared when the button is off.
      // Normalize: the field is a URLField, so a bare "example.com" (or "test") fails
      // with HTTP 400. Prepend https:// when the user omitted the scheme.
      let url = btnEnabled ? (btnUrl || '').trim() : '';
      if (url && !/^https?:\/\//i.test(url)) url = 'https://' + url;
      fd.append('button_url', url);
      fd.append('is_published', published ? 'true' : 'false');
      // DateTimeField: omit entirely when empty (DRF rejects empty strings)
      if (periodEnabled && showFrom)  fd.append('show_from',  new Date(showFrom).toISOString());
      if (periodEnabled && showUntil) fd.append('show_until', new Date(showUntil).toISOString());
      if (coverFile) fd.append('cover_image', coverFile);

      if (item) {
        await apiFetch(`/api/v1/content/news/${item.id}/`, { method: 'PATCH', body: fd, raw: true });
        toast('Новость обновлена', { type: 'success' });
      } else {
        await apiFetch('/api/v1/content/news/', { method: 'POST', body: fd, raw: true });
        toast('Новость создана', { type: 'success' });
      }
      onSaved();
    } catch (e) {
      // Surface the real validation message (e.g. «button_url: Enter a valid URL»,
      // «Обложка должна быть не больше 640 КБ») instead of a bare «HTTP 400».
      const msg = e.body
        ? Object.entries(e.body).map(([k, v]) => `${k}: ${[].concat(v).join(', ')}`).join('; ')
        : e.message;
      toast(msg || 'Ошибка сохранения', { type: 'error' });
    }
    finally { setSaving(false); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border-color)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
          {item ? 'Редактирование новости' : 'Создание новости'}
        </h2>
        <button className="icon-btn" onClick={onClose}><X size={16} /></button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 24, alignItems: 'start' }}>

          {/* ── Left: Form ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Title */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Заголовок</label>
                <span style={{ fontSize: '11px', color: title.length > 35 ? '#f59e0b' : 'var(--text-muted)' }}>
                  {title.length}/40
                </span>
              </div>
              <input value={title} onChange={e => setTitle(e.target.value.slice(0, 40))}
                placeholder="Новые поступления в магазин!" style={iStyle} />
            </div>

            {/* Body */}
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Текст новости
              </label>
              {/* Formatting toolbar */}
              <div style={{ display: 'flex', gap: 4, padding: '6px 8px',
                background: 'var(--bg-dark)', border: '1px solid var(--border-color)',
                borderRadius: '8px 8px 0 0', borderBottom: 'none' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', alignSelf: 'center', marginRight: 4 }}>
                  Обычный тек...
                </span>
                {[
                  { icon: Bold,   tag: 'b',  title: 'Жирный' },
                  { icon: Italic, tag: 'i',  title: 'Курсив' },
                  { icon: List,   tag: 'ul', title: 'Список' },
                ].map(({ icon: Icon, tag, title: t }) => (
                  <button key={tag} title={t} onClick={() => wrapSelection(tag)}
                    style={{ width: 26, height: 26, borderRadius: 5, border: '1px solid var(--border-color)',
                      background: 'var(--bg-panel)', cursor: 'pointer', color: 'var(--text-main)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon size={13} />
                  </button>
                ))}
              </div>
              <textarea ref={bodyRef} value={body} onChange={e => setBody(e.target.value)}
                rows={8} placeholder="В нашем компьютерном клубе пополнение на полках с энергетиками!"
                style={{ ...iStyle, height: 'auto', padding: '10px 12px', resize: 'vertical',
                  fontFamily: 'inherit', lineHeight: 1.6,
                  borderRadius: '0 0 8px 8px' }} />
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: 3 }}>
                Описание новости показывается в сокращённом виде — до 10 строк.
                Если текст длиннее, появится кнопка «Показать полностью».
              </div>
            </div>

            {/* Button with link */}
            <div style={{ border: '1px solid var(--border-color)', borderRadius: 10, padding: '12px 14px' }}>
              <Toggle value={btnEnabled} onChange={setBtnEnabled} label={
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Link2 size={14} style={{ color: 'var(--text-muted)' }} /> Кнопка со ссылкой
                </span>
              } />
              {btnEnabled && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Текст кнопки</label>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{btnText.length}/28</span>
                    </div>
                    <input value={btnText} onChange={e => setBtnText(e.target.value.slice(0, 28))}
                      placeholder="Ссылка на акцию" style={iStyle} />
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>URL</label>
                    <input value={btnUrl} onChange={e => setBtnUrl(e.target.value)}
                      placeholder="https://website.ru/" style={iStyle} />
                  </div>
                </div>
              )}
            </div>

            {/* Published */}
            <div style={{ border: '1px solid var(--border-color)', borderRadius: 10, padding: '12px 14px' }}>
              <Toggle value={published} onChange={setPublished} label="Опубликовано" />
            </div>

            {/* Period */}
            <div style={{ border: '1px solid var(--border-color)', borderRadius: 10, padding: '12px 14px' }}>
              <Toggle value={periodEnabled} onChange={setPeriodEnabled} label={
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Calendar size={14} style={{ color: 'var(--text-muted)' }} /> Период показа
                </span>
              } />
              {periodEnabled && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
                  <div>
                    <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>С</label>
                    <input type="datetime-local" value={showFrom} onChange={e => setShowFrom(e.target.value)}
                      style={{ ...iStyle, colorScheme: 'dark' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>По</label>
                    <input type="datetime-local" value={showUntil} onChange={e => setShowUntil(e.target.value)}
                      style={{ ...iStyle, colorScheme: 'dark' }} />
                  </div>
                </div>
              )}
              {periodEnabled && (showFrom || showUntil) && (
                <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 6,
                  padding: '6px 10px', background: 'var(--hover-overlay)', borderRadius: 6 }}>
                  <Calendar size={12} style={{ color: 'var(--accent)' }} />
                  <span style={{ fontSize: '12px', color: 'var(--accent)' }}>
                    {showFrom ? new Date(showFrom).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) : '∞'}
                    {' — '}
                    {showUntil ? new Date(showUntil).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) : '∞'}
                  </span>
                </div>
              )}
            </div>

            {/* Save button */}
            <button className="btn btn-primary" style={{ height: 44, justifyContent: 'center', fontSize: '14px' }}
              onClick={save} disabled={saving}>
              {saving ? 'Сохранение…' : item ? 'Сохранить' : 'Создать'}
            </button>
          </div>

          {/* ── Right: Cover + Preview ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Cover upload */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>Обложка</span>
                <span title="Мин. 312×176, опт. 624×352, 16:9, ≤640 КБ"
                  style={{ width: 16, height: 16, borderRadius: '50%', border: '1px solid var(--text-muted)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '10px', color: 'var(--text-muted)', cursor: 'help', flexShrink: 0 }}>
                  i
                </span>
              </div>
              <div onClick={() => fileRef.current?.click()}
                style={{ width: '100%', aspectRatio: '16/9', borderRadius: 10, overflow: 'hidden',
                  border: `2px dashed ${coverPreview ? 'transparent' : 'var(--border-color)'}`,
                  cursor: 'pointer', position: 'relative', background: 'var(--bg-dark)' }}>
                {coverPreview ? (
                  <>
                    <img src={coverPreview} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                    <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      opacity: 0, transition: 'opacity 0.2s' }}
                      onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                      onMouseLeave={e => e.currentTarget.style.opacity = '0'}>
                      <ImageIcon size={24} color="#fff" />
                    </div>
                  </>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center',
                    justifyContent: 'center', height: '100%', gap: 8 }}>
                    <ImageIcon size={28} style={{ opacity: 0.3 }} />
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Загрузить изображение</span>
                  </div>
                )}
              </div>
              <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp"
                onChange={onFileChange} style={{ display: 'none' }} />
            </div>

            {/* Preview */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                <Eye size={13} style={{ color: 'var(--text-muted)' }} />
                <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>Предпросмотр новости</span>
              </div>
              <NewsPreview
                title={title}
                body={body}
                buttonText={btnEnabled ? btnText : ''}
                coverUrl={coverPreview}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ─── Row context menu ────────────────────────────────────────────────── */
const RowMenu = ({ onEdit, onDelete, onClose }) => {
  const ref = useRef();
  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) onClose(); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [onClose]);

  return (
    <div ref={ref} style={{ position: 'absolute', right: 8, top: '100%', marginTop: 4,
      background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
      borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.35)', zIndex: 50,
      padding: 6, minWidth: 160 }}>
      <div onClick={onEdit}
        style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
          borderRadius: 6, cursor: 'pointer', fontSize: '13px' }}
        onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
        <Edit2 size={13} style={{ color: 'var(--text-muted)' }} /> Редактировать
      </div>
      <div onClick={onDelete}
        style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px',
          borderRadius: 6, cursor: 'pointer', fontSize: '13px', color: '#ef4444' }}
        onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.08)'}
        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
        <Trash2 size={13} /> Удалить
      </div>
    </div>
  );
};

/* ─── Main News component ─────────────────────────────────────────────── */
const News = () => {
  const { toast } = useToast();
  const clubId = localStorage.getItem('active_club_id');

  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab]         = useState('published');   // 'published' | 'draft'
  const [form, setForm]       = useState(null);          // null | { item? }
  const [openMenuId, setOpenMenuId] = useState(null);
  const [sortCol, setSortCol] = useState('created_at');
  const [sortDir, setSortDir] = useState(-1);

  /* ── load ── */
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await apiFetch(`/api/v1/content/news/?club=${clubId || ''}`);
      setItems(r.results || r || []);
    } catch (e) { toast(e.message, { type: 'error' }); }
    finally { setLoading(false); }
  }, [clubId]); // eslint-disable-line

  useEffect(() => { load(); }, [load]);

  /* ── delete ── */
  const deleteItem = async (id) => {
    if (!window.confirm('Удалить новость?')) return;
    try {
      await apiFetch(`/api/v1/content/news/${id}/`, { method: 'DELETE' });
      toast('Новость удалена', { type: 'success' });
      setItems(p => p.filter(x => x.id !== id));
    } catch (e) { toast(e.message, { type: 'error' }); }
  };

  /* ── sort & filter ── */
  const filtered = items
    .filter(n => tab === 'published' ? n.is_published : !n.is_published)
    .sort((a, b) => {
      const av = a[sortCol] || '';
      const bv = b[sortCol] || '';
      return String(av).localeCompare(String(bv), 'ru') * sortDir;
    });

  const toggleSort = (col) => {
    if (sortCol === col) setSortDir(d => -d);
    else { setSortCol(col); setSortDir(1); }
  };
  const Arrow = ({ col }) => (
    <span style={{ marginLeft: 3, opacity: sortCol === col ? 1 : 0.3, color: 'var(--accent)' }}>
      {sortCol === col ? (sortDir === 1 ? '↑' : '↓') : '↕'}
    </span>
  );

  /* ── If form is open, show form view ── */
  if (form !== null) {
    return (
      <NewsForm
        item={form.item || null}
        clubId={clubId}
        onClose={() => setForm(null)}
        onSaved={() => { setForm(null); load(); }}
      />
    );
  }

  /* ── List view ── */
  return (
    <div style={{ padding: '0 24px', display: 'flex', flexDirection: 'column', gap: 14, height: '100%' }}>

      {/* Header row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10, flexShrink: 0 }}>

        {/* Tab pills */}
        <div style={{ display: 'flex', gap: 4 }}>
          {[
            { id: 'published', label: 'Опубликованные' },
            { id: 'draft',     label: 'Неопубликованные' },
          ].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{ padding: '7px 16px', borderRadius: 8, fontSize: '13px', fontWeight: 500,
                cursor: 'pointer', fontFamily: 'inherit', border: 'none',
                background: tab === t.id ? 'var(--bg-panel)' : 'transparent',
                color: tab === t.id ? 'var(--text-main)' : 'var(--text-muted)',
                boxShadow: tab === t.id ? '0 1px 3px rgba(0,0,0,0.3)' : 'none' }}>
              {t.label}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary" onClick={load} disabled={loading}><RefreshCw size={14} /></button>
          <button className="btn btn-primary" onClick={() => setForm({})}
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Plus size={14} /> Создать новость
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Загрузка…</div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)',
            background: 'var(--bg-panel)', borderRadius: 12, border: '1px solid var(--border-color)' }}>
            <Newspaper size={36} style={{ opacity: 0.25, marginBottom: 12 }} />
            <div>{tab === 'published' ? 'Нет опубликованных новостей' : 'Нет черновиков'}</div>
          </div>
        ) : (
          <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
            borderRadius: 12, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-dark)' }}>
                  {/* sort indicator column */}
                  <th style={{ width: 28, padding: '10px 6px 10px 14px' }}>
                    <ChevronDown size={12} style={{ color: 'var(--text-muted)', opacity: 0.4 }} />
                  </th>
                  {/* image */}
                  <th style={{ width: 90 }} />
                  {[
                    { col: 'title',      label: 'Заголовок' },
                    { col: 'show_from',  label: 'Начало периода' },
                    { col: 'show_until', label: 'Конец периода' },
                    { col: 'button_text', label: 'Текст кнопки' },
                    { col: 'body',       label: 'Текст новости' },
                    { col: 'created_at', label: 'Дата создания' },
                  ].map(({ col, label }) => (
                    <th key={col} onClick={() => toggleSort(col)}
                      style={{ padding: '10px 12px', textAlign: 'left', fontSize: '10px',
                        color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase',
                        letterSpacing: '0.5px', cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' }}>
                      {label} <Arrow col={col} />
                    </th>
                  ))}
                  <th style={{ width: 40 }} />
                </tr>
              </thead>
              <tbody>
                {filtered.map(n => (
                  <tr key={n.id}
                    style={{ borderBottom: '1px solid var(--border-row)', cursor: 'default' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--hover-overlay)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>

                    {/* Sort handle */}
                    <td style={{ padding: '10px 6px 10px 14px' }}>
                      <ChevronUp size={11} style={{ color: 'var(--text-muted)', opacity: 0.3, display: 'block' }} />
                      <ChevronDown size={11} style={{ color: 'var(--text-muted)', opacity: 0.3, display: 'block' }} />
                    </td>

                    {/* Thumbnail */}
                    <td style={{ padding: '8px 10px' }}>
                      <img
                        src={n.cover_image_url || `https://picsum.photos/seed/news-${n.id}/160/90`}
                        alt=""
                        style={{ width: 72, height: 40, borderRadius: 6, objectFit: 'cover', display: 'block' }}
                        onError={e => { e.target.src = `https://picsum.photos/seed/news-${n.id}/160/90`; }}
                      />
                    </td>

                    {/* Title */}
                    <td style={{ padding: '8px 12px', fontWeight: 600, maxWidth: 200,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {n.title}
                    </td>

                    {/* Start */}
                    <td style={{ padding: '8px 12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {fmtDate(n.show_from)}
                    </td>

                    {/* End */}
                    <td style={{ padding: '8px 12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {fmtDate(n.show_until)}
                    </td>

                    {/* Button text */}
                    <td style={{ padding: '8px 12px' }}>
                      {n.button_text ? (
                        <span style={{ fontSize: '12px', color: 'var(--accent)' }}>{n.button_text}</span>
                      ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                    </td>

                    {/* Body */}
                    <td style={{ padding: '8px 12px', maxWidth: 320 }}>
                      {/* BUGFIX: this "Текст новости" column showed n.title (already
                          shown in its own column). Show the news body instead. */}
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {n.body?.replace(/<[^>]+>/g, '') || '—'}
                      </div>
                    </td>

                    {/* Created */}
                    <td style={{ padding: '8px 12px', color: 'var(--text-muted)', whiteSpace: 'nowrap', fontSize: '12px' }}>
                      {fmtDateTime(n.created_at)}
                    </td>

                    {/* Actions — direct buttons. The old dropdown (position:absolute inside
                        the table) got clipped by the table overflow, so «Редактировать»
                        was invisible/unclickable. Direct icon buttons can't be clipped. */}
                    <td style={{ padding: '8px 8px', whiteSpace: 'nowrap' }}>
                      <button className="icon-btn" title="Редактировать"
                        style={{ width: 28, height: 28 }}
                        onClick={() => setForm({ item: n })}>
                        <Edit2 size={14} />
                      </button>
                      <button className="icon-btn" title="Удалить"
                        style={{ width: 28, height: 28, marginLeft: 4, color: '#ef4444' }}
                        onClick={() => deleteItem(n.id)}>
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default News;
