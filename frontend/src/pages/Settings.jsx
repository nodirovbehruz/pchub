import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Settings as SettingsIcon, Monitor, Shield, Palette, Star, Plug, Save,
  Building2, ToggleLeft, ToggleRight, RefreshCw, Download, Plus, X,
  Eye, EyeOff, Upload, Scale, Search, AlertCircle,
} from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

/* ─── tiny helpers ────────────────────────────────────────────────────── */
const sel = {
  height: '36px', padding: '0 12px', background: 'var(--bg-input)',
  border: '1px solid var(--border-input)', borderRadius: '8px',
  color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit',
};

const Inp = ({ value, onChange, placeholder, type = 'text', style = {}, min, max }) => (
  <input type={type} value={value ?? ''} onChange={onChange} placeholder={placeholder}
    min={min} max={max}
    style={{ height: '36px', padding: '0 12px', width: '100%',
      background: 'var(--bg-input)', border: '1px solid var(--border-input)',
      borderRadius: '8px', color: 'var(--text-main)', fontSize: '13px',
      fontFamily: 'inherit', ...style }} />
);

const Tog = ({ value, onChange, label }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
    <button onClick={() => onChange(!value)}
      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0,
        color: value ? '#10b981' : 'var(--text-muted)', display: 'flex' }}>
      {value ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
    </button>
    {label && <span style={{ fontSize: '13px', color: value ? 'var(--text-main)' : 'var(--text-muted)' }}>{label}</span>}
  </div>
);

// BUGFIX(#5): when `max` is given, clamp the entered value into [min, max] on
// change. The `min`/`max` HTML attributes alone DON'T stop a user typing 250 into
// a percent field — the out-of-range value still reaches state and gets saved
// (e.g. bonus_writeoff_pct=250). Clamping here hard-bounds it in the UI.
const Num = ({ value, onChange, placeholder, min = 0, max, style = {} }) => {
  const handle = (e) => {
    if (max === undefined) { onChange(e); return; }
    const raw = e.target.value;
    if (raw === '') { onChange(e); return; } // allow clearing the field
    let n = Number(raw);
    if (Number.isNaN(n)) return;             // ignore non-numeric junk
    n = Math.max(min, Math.min(max, n));
    onChange({ ...e, target: { ...e.target, value: String(n) } });
  };
  return (
    <Inp type="number" value={value} onChange={handle} placeholder={placeholder}
      min={min} max={max} style={{ width: '100px', ...style }} />
  );
};

const Row = ({ label, hint, children, last }) => (
  <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '16px',
    alignItems: 'flex-start', padding: '11px 0',
    borderBottom: last ? 'none' : '1px solid var(--border-row)' }}>
    <div>
      <div style={{ fontSize: '13px', fontWeight: 500 }}>{label}</div>
      {hint && <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{hint}</div>}
    </div>
    <div style={{ display: 'flex', alignItems: 'center' }}>{children}</div>
  </div>
);

const Sec = ({ title, children }) => (
  <div style={{ background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
    borderRadius: '12px', overflow: 'hidden', marginBottom: '16px' }}>
    {title && (
      <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border-color)',
        fontWeight: 600, fontSize: '13px', color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {title}
      </div>
    )}
    <div style={{ padding: '0 20px 4px' }}>{children}</div>
  </div>
);

const Sel = ({ value, onChange, options, style = {} }) => (
  <select value={value ?? ''} onChange={onChange} style={{ ...sel, ...style }}>
    {options.map(o => <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>)}
  </select>
);

/* ─── TABS config ─────────────────────────────────────────────────────── */
const TABS = [
  { id: 'club',        label: 'Клуб',              icon: Building2 },
  { id: 'legal',       label: 'Юридические',        icon: Scale },
  { id: 'panel',       label: 'Панель управления',  icon: Monitor },
  { id: 'shell',       label: 'Шелл',               icon: SettingsIcon },
  { id: 'security',    label: 'Безопасность',        icon: Shield },
  { id: 'custom',      label: 'Кастомизация',        icon: Palette },
  { id: 'smartgamer',  label: 'HUB APP',             icon: Star },
  { id: 'integrations',label: 'Интеграции',          icon: Plug },
];

/* ═══════════════════════════════════════════════════════════════════════
   TAB 1 — Профиль клуба
══════════════════════════════════════════════════════════════════════ */
const DAYS = [
  { key: 'mon', label: 'Пн' }, { key: 'tue', label: 'Вт' }, { key: 'wed', label: 'Ср' },
  { key: 'thu', label: 'Чт' }, { key: 'fri', label: 'Пт' }, { key: 'sat', label: 'Сб' },
  { key: 'sun', label: 'Вс' },
];
const DEFAULT_DAY = { open: '10:00', close: '23:00', closed: false };

const ClubTab = ({ club, onChange, s, upd }) => {
  const { toast } = useToast(); // BUGFIX: token-regenerate handler called undefined `toast` → ReferenceError crash
  const schedule = s.work_schedule || {};
  const equipment = s.equipment_list || [];
  const services  = s.club_services  || [];
  const photos    = s.club_photos    || [];
  const [newEquip, setNewEquip] = useState({ name: '', desc: '' });
  const [newSvc,   setNewSvc]   = useState({ name: '', desc: '' });
  const [newPhoto, setNewPhoto] = useState('');

  const setDay = (key, field, val) => {
    const d = { ...DEFAULT_DAY, ...(schedule[key] || {}), [field]: val };
    upd('work_schedule', { ...schedule, [key]: d });
  };

  return (
    <div>
      {/* ── Основная информация ──────────────────────────────── */}
      <Sec title="Основная информация">
        <Row label="Название клуба" hint="Отображается в шелле, на карте и в приложении">
          <Inp value={club.name} onChange={e => onChange('name', e.target.value)} placeholder="Мой клуб" />
        </Row>
        <Row label="Описание" hint="Видно клиентам в мобильном приложении">
          <textarea value={s.description || ''} onChange={e => upd('description', e.target.value)}
            rows={3} placeholder="Расскажите о вашем клубе: атмосфера, особенности, фишки..."
            style={{ width: '100%', background: 'var(--bg-input)', border: '1px solid var(--border-input)',
              borderRadius: '8px', color: 'var(--text-main)', fontSize: '13px',
              fontFamily: 'inherit', padding: '10px 12px', resize: 'vertical', lineHeight: 1.5 }} />
        </Row>
        <Row label="Сайт / Соцсети">
          <Inp value={club.site} onChange={e => onChange('site', e.target.value)} placeholder="https://mygamingclub.ru" />
        </Row>
        <Row label="Телефон (публичный)" hint="Для клиентов в приложении">
          <Inp value={club.phone} onChange={e => onChange('phone', e.target.value)} placeholder="+7 (900) 000-00-00" />
        </Row>
        <Row label="Контактное лицо" hint="Только для нас — кому писать по вопросам платформы">
          <Inp value={club.contact_name} onChange={e => onChange('contact_name', e.target.value)} placeholder="Иван Петров" />
        </Row>
        <Row label="Email" last>
          <Inp value={club.email} onChange={e => onChange('email', e.target.value)} type="email" placeholder="info@club.ru" />
        </Row>
      </Sec>

      {/* ── Адрес ───────────────────────────────────────────── */}
      <Sec title="Адрес">
        <Row label="Страна">
          <Inp value={club.country} onChange={e => onChange('country', e.target.value)} placeholder="Россия" style={{ maxWidth: '200px' }} />
        </Row>
        <Row label="Город">
          <Inp value={club.city} onChange={e => onChange('city', e.target.value)} placeholder="Москва" style={{ maxWidth: '240px' }} />
        </Row>
        <Row label="Улица">
          <Inp value={club.street} onChange={e => onChange('street', e.target.value)} placeholder="ул. Примерная" />
        </Row>
        <Row label="Дом / корпус" last>
          <Inp value={club.house} onChange={e => onChange('house', e.target.value)} placeholder="д. 1, корп. 2" style={{ maxWidth: '160px' }} />
        </Row>
      </Sec>

      {/* ── График работы ─────────────────────────────────── */}
      <Sec title="График работы">
        <div style={{ padding: '8px 0 4px' }}>
          {DAYS.map(({ key, label }) => {
            const d = { ...DEFAULT_DAY, ...(schedule[key] || {}) };
            return (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '12px',
                padding: '7px 0', borderBottom: '1px solid var(--border-row)' }}>
                <span style={{ width: '28px', fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>{label}</span>
                <Tog value={!d.closed} onChange={v => setDay(key, 'closed', !v)} />
                {!d.closed ? (
                  <>
                    <Inp type="time" value={d.open} onChange={e => setDay(key, 'open', e.target.value)}
                      style={{ width: '100px' }} />
                    <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>—</span>
                    <Inp type="time" value={d.close} onChange={e => setDay(key, 'close', e.target.value)}
                      style={{ width: '100px' }} />
                  </>
                ) : (
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>Выходной</span>
                )}
              </div>
            );
          })}
        </div>
      </Sec>

      {/* ── Оборудование ───────────────────────────────────── */}
      <Sec title="Оборудование">
        <Row label="Список оборудования" hint="Клиенты видят в приложении, чтобы выбрать зону" last>
          <div style={{ width: '100%' }}>
            {equipment.map((e, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px',
                padding: '7px 12px', marginBottom: '4px',
                background: 'var(--hover-overlay)', borderRadius: '8px' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '13px', fontWeight: 500 }}>{e.name}</div>
                  {e.desc && <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{e.desc}</div>}
                </div>
                <button className="icon-btn" onClick={() => upd('equipment_list', equipment.filter((_, j) => j !== i))}>
                  <X size={13} />
                </button>
              </div>
            ))}
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <Inp value={newEquip.name} onChange={e => setNewEquip(p => ({ ...p, name: e.target.value }))}
                placeholder="Игровые ПК" style={{ flex: 1 }} />
              <Inp value={newEquip.desc} onChange={e => setNewEquip(p => ({ ...p, desc: e.target.value }))}
                placeholder="32 шт, RTX 4070" style={{ flex: 1 }} />
              <button className="btn btn-secondary" style={{ height: '36px', padding: '0 14px', fontSize: '12px', flexShrink: 0 }}
                onClick={() => {
                  if (!newEquip.name.trim()) return;
                  upd('equipment_list', [...equipment, { ...newEquip }]);
                  setNewEquip({ name: '', desc: '' });
                }}><Plus size={13} /></button>
            </div>
          </div>
        </Row>
      </Sec>

      {/* ── Услуги клуба ───────────────────────────────────── */}
      <Sec title="Услуги клуба">
        <Row label="Доп. услуги" hint="Показываются клиентам в мобильном приложении" last>
          <div style={{ width: '100%' }}>
            {services.map((sv, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px',
                padding: '7px 12px', marginBottom: '4px',
                background: 'var(--hover-overlay)', borderRadius: '8px' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '13px', fontWeight: 500 }}>{sv.name}</div>
                  {sv.desc && <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{sv.desc}</div>}
                </div>
                <button className="icon-btn" onClick={() => upd('club_services', services.filter((_, j) => j !== i))}>
                  <X size={13} />
                </button>
              </div>
            ))}
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              <Inp value={newSvc.name} onChange={e => setNewSvc(p => ({ ...p, name: e.target.value }))}
                placeholder="Турниры" style={{ flex: 1 }} />
              <Inp value={newSvc.desc} onChange={e => setNewSvc(p => ({ ...p, desc: e.target.value }))}
                placeholder="Еженедельные соревнования" style={{ flex: 1 }} />
              <button className="btn btn-secondary" style={{ height: '36px', padding: '0 14px', fontSize: '12px', flexShrink: 0 }}
                onClick={() => {
                  if (!newSvc.name.trim()) return;
                  upd('club_services', [...services, { ...newSvc }]);
                  setNewSvc({ name: '', desc: '' });
                }}><Plus size={13} /></button>
            </div>
          </div>
        </Row>
      </Sec>

      {/* ── Фото клуба ─────────────────────────────────────── */}
      <Sec title="Фото клуба">
        <Row label="Галерея" hint="URL фотографий, видны клиентам в приложении" last>
          <div style={{ width: '100%' }}>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
              {photos.map((url, i) => (
                <div key={i} style={{ position: 'relative', width: '80px', height: '56px' }}>
                  <img src={url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover',
                    borderRadius: '6px', border: '1px solid var(--border-color)' }}
                    onError={e => { e.target.style.display = 'none'; }} />
                  <button onClick={() => upd('club_photos', photos.filter((_, j) => j !== i))}
                    style={{ position: 'absolute', top: '-6px', right: '-6px', width: '18px', height: '18px',
                      borderRadius: '50%', background: '#ef4444', border: 'none', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                    <X size={10} />
                  </button>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <Inp value={newPhoto} onChange={e => setNewPhoto(e.target.value)}
                placeholder="https://example.com/photo.jpg" style={{ flex: 1 }} />
              <button className="btn btn-secondary" style={{ height: '36px', padding: '0 14px', fontSize: '12px', flexShrink: 0 }}
                onClick={() => {
                  if (!newPhoto.trim()) return;
                  upd('club_photos', [...photos, newPhoto.trim()]);
                  setNewPhoto('');
                }}>
                <Plus size={13} />
              </button>
            </div>
          </div>
        </Row>
      </Sec>

      {/* ── Токен клуба ────────────────────────────────────── */}
      <Sec title="Токен клуба">
        <Row label="Club Token" hint="Вводится при установке шелла на клиентский ПК — ПК автоматически привяжется к этому клубу" last>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <div style={{
              fontFamily: 'monospace', fontSize: '22px', fontWeight: 700, letterSpacing: '4px',
              padding: '10px 20px', background: 'rgba(99,102,241,0.1)',
              border: '2px dashed rgba(99,102,241,0.4)', borderRadius: '10px',
              color: '#818cf8', userSelect: 'all', minWidth: '160px', textAlign: 'center',
            }}>
              {club.club_token || '—'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <button
                className="btn btn-secondary"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
                onClick={async () => {
                  const id = localStorage.getItem('active_club_id');
                  if (!id) return;
                  if (!window.confirm('Сгенерировать новый токен? Все ПК с текущим токеном потеряют привязку.')) return;
                  try {
                    const res = await apiFetch(`/api/v1/clubs/${id}/regenerate-token/`, { method: 'POST' });
                    onChange('club_token', res.club_token);
                    toast('Токен обновлён', { type: 'success' });
                  } catch (e) {
                    toast('Ошибка обновления токена', { type: 'error' });
                  }
                }}>
                🔄 Сгенерировать новый
              </button>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Покажи этот код при настройке нового ПК
              </div>
            </div>
          </div>
        </Row>
      </Sec>

      {/* ── Региональные настройки ──────────────────────────── */}
      <Sec title="Региональные настройки">
        <Row label="Часовой пояс" last>
          <Sel value={club.timezone} onChange={e => onChange('timezone', e.target.value)} style={{ width: '260px' }}
            options={['Europe/Moscow','Europe/Kaliningrad','Asia/Yekaterinburg','Asia/Novosibirsk',
              'Asia/Krasnoyarsk','Asia/Irkutsk','Asia/Yakutsk','Asia/Vladivostok',
              'Asia/Almaty','Asia/Tashkent'].map(v => ({ value: v, label: v }))} />
        </Row>
      </Sec>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════════
   TAB 2 — Юридические данные (Реквизиты + ПОПД)
══════════════════════════════════════════════════════════════════════ */
const LegalTab = ({ s, upd }) => {
  const [innLoading, setInnLoading] = useState(false);
  const [innError, setInnError]     = useState('');

  const lookupInn = async () => {
    const inn = (s.inn || '').trim().replace(/\D/g, '');
    if (inn.length !== 10 && inn.length !== 12) {
      setInnError('ИНН должен быть 10 цифр (ООО/АО) или 12 цифр (ИП)');
      return;
    }
    const clubId = localStorage.getItem('active_club_id');
    setInnError('');
    setInnLoading(true);
    try {
      // Via our backend proxy — the browser can't call DaData directly (CORS),
      // and the API key stays server-side.
      const data = await apiFetch(`/api/v1/clubs/${clubId}/dadata/party/?inn=${inn}`);
      if (data?.found) {
        upd('legal_name',    data.legal_name    || '');
        upd('legal_address', data.legal_address || '');
        upd('ogrn',          data.ogrn          || '');
      } else {
        setInnError('Организация с таким ИНН не найдена');
      }
    } catch (e) {
      setInnError(e.body?.error || 'Ошибка запроса к DaData (проверьте API-ключ в Интеграциях)');
    } finally {
      setInnLoading(false);
    }
  };

  return (
    <div>
      {/* Info banner */}
      <div style={{ display: 'flex', gap: '12px', background: 'rgba(99,102,241,0.08)',
        border: '1px solid rgba(99,102,241,0.25)', borderRadius: '12px',
        padding: '14px 18px', marginBottom: '16px', alignItems: 'flex-start' }}>
        <AlertCircle size={18} style={{ color: '#818cf8', flexShrink: 0, marginTop: '1px' }} />
        <div style={{ fontSize: '13px', lineHeight: 1.55, color: 'var(--text-main)' }}>
          <strong>Юридические данные</strong> необходимы для выгрузки базы клиентов согласно
          ФЗ № 152-ФЗ «О персональных данных». ПОПД принимается клиентами в шелле при первом визите.
        </div>
      </div>

      <Sec title="Реквизиты организации">
        <Row label="ИНН" hint="10 цифр для ООО/АО, 12 цифр для ИП">
          <div style={{ width: '100%' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <Inp value={s.inn || ''} placeholder="7841079647"
                onChange={e => { upd('inn', e.target.value.replace(/\D/g,'').slice(0,12)); setInnError(''); }}
                style={{ flex: 1, maxWidth: '280px' }} />
              <button className="btn btn-secondary" onClick={lookupInn} disabled={innLoading}
                style={{ height: '36px', padding: '0 16px', fontSize: '12px',
                  display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                {innLoading
                  ? <RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} />
                  : <Search size={13} />}
                Найти по ИНН
              </button>
            </div>
            {innError && (
              <div style={{ fontSize: '12px', color: '#ef4444', marginTop: '6px',
                display: 'flex', alignItems: 'center', gap: '4px' }}>
                <AlertCircle size={12} /> {innError}
              </div>
            )}
          </div>
        </Row>

        <Row label="Наименование" hint="Полное юридическое название">
          <Inp value={s.legal_name || ''} placeholder="ООО «Рога и Копыта»"
            onChange={e => upd('legal_name', e.target.value)} />
        </Row>

        <Row label="Юридический адрес" hint="Адрес регистрации организации">
          <Inp value={s.legal_address || ''} placeholder="109004, г. Москва, ул. Примерная, д. 1"
            onChange={e => upd('legal_address', e.target.value)} />
        </Row>

        <Row label="ОГРН / ОГРНИП" hint="Основной государственный регистрационный номер">
          <Inp value={s.ogrn || ''} placeholder="1187847365496"
            onChange={e => upd('ogrn', e.target.value.replace(/\D/g,'').slice(0,15))}
            style={{ maxWidth: '220px' }} />
        </Row>

        <Row label="Контактный e-mail" hint="Для юридической переписки" last>
          <Inp type="email" value={s.legal_email || ''} placeholder="ivanov@mail.ru"
            onChange={e => upd('legal_email', e.target.value)}
            style={{ maxWidth: '320px' }} />
        </Row>
      </Sec>

      <Sec title="ПОПД — Политика обработки персональных данных">
        <div style={{ padding: '12px 0 6px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px', lineHeight: 1.6 }}>
            Введите полный текст политики обработки персональных данных вашего клуба.
            Клиенты будут обязаны принять её в клиентском шелле при первом посещении.
            При изменении документа все клиенты должны принять обновлённую версию.
          </div>
          <textarea
            value={s.popd_text || ''}
            onChange={e => upd('popd_text', e.target.value)}
            rows={16}
            placeholder={`1. Общие положения\nНастоящая Политика обработки персональных данных (далее — «Политика») определяет порядок обработки и защиты персональных данных клиентов, посетителей и пользователей услуг компьютерного клуба (далее — «Клуб»).\nПолитика разработана в соответствии с требованиями Федерального закона РФ №152-ФЗ «О персональных данных».\n\n2. Перечень персональных данных\n— Фамилия, имя, отчество\n— Номер телефона\n— Адрес электронной почты\n\n3. Цели обработки\nПерсональные данные обрабатываются в целях идентификации клиента, предоставления услуг клуба, информирования об акциях.`}
            style={{
              width: '100%', background: 'var(--bg-input)',
              border: '1px solid var(--border-input)', borderRadius: '8px',
              color: 'var(--text-main)', fontSize: '13px', fontFamily: 'inherit',
              padding: '14px', resize: 'vertical', lineHeight: 1.65,
            }} />
        </div>
      </Sec>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px',
        padding: '12px 20px', background: 'var(--bg-panel)',
        border: '1px solid var(--border-color)', borderRadius: '12px' }}>
        <input type="checkbox" id="legal_confirmed"
          checked={!!s.legal_confirmed}
          onChange={e => upd('legal_confirmed', e.target.checked)}
          style={{ width: '16px', height: '16px', accentColor: 'var(--accent)', cursor: 'pointer', flexShrink: 0 }} />
        <label htmlFor="legal_confirmed"
          style={{ fontSize: '13px', cursor: 'pointer', color: 'var(--text-main)' }}>
          Подтверждаю достоверность указанной информации
        </label>
      </div>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════════
   TAB 3 — Панель управления
══════════════════════════════════════════════════════════════════════ */
const PanelTab = ({ s, upd }) => {
  const [newDate, setNewDate] = useState('');
  const holidayDates = s.holiday_dates || [];

  const addDate = () => {
    if (!newDate) return;
    upd('holiday_dates', [...holidayDates, newDate]);
    setNewDate('');
  };
  const removeDate = (d) => upd('holiday_dates', holidayDates.filter(x => x !== d));

  return (
    <div>
      {/* Тарифы */}
      <Sec title="Тарифы">
        <Row label="Автозапуск минутного тарифа" hint="Сеанс начинается сразу при входе клиента">
          <Tog value={s.auto_launch_minute_tariff} onChange={v => upd('auto_launch_minute_tariff', v)} label="Включено" />
        </Row>
        <Row label="Автоматические сеансы" hint="Клиент входит — сеанс создаётся автоматически">
          <Tog value={s.auto_session} onChange={v => upd('auto_session', v)} label="Включено" />
        </Row>
        <Row label="Праздничный тариф" hint="Особая ставка в праздничные дни">
          <Tog value={s.holiday_tariff} onChange={v => upd('holiday_tariff', v)} label="Включено" />
        </Row>
        {s.holiday_tariff && (
          <Row label="Праздничные даты" hint="ДД.ММ или ДД.ММ.ГГГГ" last>
            <div style={{ width: '100%' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '8px' }}>
                {holidayDates.map(d => (
                  <span key={d} style={{ display: 'flex', alignItems: 'center', gap: '4px',
                    padding: '3px 10px', background: 'rgba(99,102,241,0.15)',
                    borderRadius: '20px', fontSize: '12px', color: '#818cf8' }}>
                    {d}
                    <button onClick={() => removeDate(d)} style={{ background: 'none', border: 'none',
                      cursor: 'pointer', color: '#818cf8', padding: 0, display: 'flex' }}>
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <Inp value={newDate} onChange={e => setNewDate(e.target.value)} placeholder="01.01.2025"
                  style={{ width: '160px' }} />
                <button className="btn btn-secondary" style={{ padding: '0 14px', height: '36px', fontSize: '12px' }}
                  onClick={addDate}>Добавить</button>
              </div>
            </div>
          </Row>
        )}
      </Sec>

      {/* Сеансы */}
      <Sec title="Сеансы">
        <Row label="Завершить перед бронью (мин)" hint="За сколько минут до начала брони завершить сеанс">
          <Num value={s.end_before_booking_min} onChange={e => upd('end_before_booking_min', e.target.value)} placeholder="5" />
        </Row>
        <Row label="Истечение брони (мин)" hint="Через сколько минут не пришедшая бронь отменяется">
          <Num value={s.booking_expiry_min} onChange={e => upd('booking_expiry_min', e.target.value)} placeholder="15" />
        </Row>
        <Row label="Показывать сеансы на карте">
          <Tog value={s.show_sessions_map} onChange={v => upd('show_sessions_map', v)} label="Включено" />
        </Row>
        <Row label="Блокировать депозит (виртуальные хосты)">
          <Tog value={s.block_deposit_virtual} onChange={v => upd('block_deposit_virtual', v)} label="Включено" />
        </Row>
        <Row label="Постоплата" hint="Начало сеанса без предварительной оплаты">
          <Tog value={s.postpayment} onChange={v => upd('postpayment', v)} label="Включено" />
        </Row>
        <Row label="Макс. продолжительность сеанса (мин)" hint="0 — без ограничений" last>
          <Num value={s.max_session_duration} onChange={e => upd('max_session_duration', e.target.value)} placeholder="0" />
        </Row>
      </Sec>

      {/* Система лояльности */}
      <Sec title="Система лояльности">
        <Row label="Бонусная система">
          <Tog value={s.bonus_system} onChange={v => upd('bonus_system', v)} label="Включено" />
        </Row>
        <Row label="Бонусы операторам">
          <Tog value={s.operator_bonuses} onChange={v => upd('operator_bonuses', v)} label="Включено" />
        </Row>
        <Row label="Оплата тарифов бонусами">
          <Tog value={s.bonus_pay_tariffs} onChange={v => upd('bonus_pay_tariffs', v)} label="Включено" />
        </Row>
        <Row label="Процент списания бонусов" hint="Максимальная доля оплаты бонусами (%)">
          <Num value={s.bonus_writeoff_pct} onChange={e => upd('bonus_writeoff_pct', e.target.value)} placeholder="50" min={0} max={100} />
          <span style={{ marginLeft: '6px', fontSize: '13px', color: 'var(--text-muted)' }}>%</span>
        </Row>
        <Row label="Автоприменение персональной скидки" last>
          <Tog value={s.personal_discount_auto} onChange={v => upd('personal_discount_auto', v)} label="Включено" />
        </Row>
      </Sec>

      {/* Рабочая смена */}
      <Sec title="Рабочая смена">
        <Row label="Отмена платежей">
          <Tog value={s.allow_payment_cancel} onChange={v => upd('allow_payment_cancel', v)} label="Разрешено" />
        </Row>
        <Row label="Период отмены (мин)" hint="В течение скольки минут можно отменить платёж">
          <Num value={s.cancel_period_min} onChange={e => upd('cancel_period_min', e.target.value)} placeholder="5" />
        </Row>
        <Row label="Обязательная печать отчёта при закрытии смены">
          <Tog value={s.mandatory_report} onChange={v => upd('mandatory_report', v)} label="Включено" />
        </Row>
        <Row label="Печатать остатки товаров" last>
          <Tog value={s.print_stock_list} onChange={v => upd('print_stock_list', v)} label="Включено" />
        </Row>
      </Sec>

      {/* Авторизация */}
      <Sec title="Авторизация">
        <Row label="Регистрация клиентов оператором" hint="Оператор может регистрировать новых клиентов" last>
          <Tog value={s.operator_client_registration} onChange={v => upd('operator_client_registration', v)} label="Включено" />
        </Row>
      </Sec>

      {/* Общее */}
      <Sec title="Общее">
        <Row label="Валюта">
          <Sel value={s.currency} onChange={e => upd('currency', e.target.value)} style={{ width: '220px' }}
            options={[
              { value: 'UZS', label: 'Узбекский сум (сум)' },
              { value: 'RUB', label: 'Российский рубль (₽)' },
              { value: 'KZT', label: 'Казахстанский тенге (₸)' },
              { value: 'USD', label: 'Доллар США ($)' },
            ]} />
        </Row>
        <Row label="Язык интерфейса" last>
          <Sel value={s.ui_language} onChange={e => upd('ui_language', e.target.value)} style={{ width: '180px' }}
            options={[
              { value: 'ru', label: 'Русский' },
              { value: 'en', label: 'English' },
              { value: 'kz', label: 'Қазақша' },
            ]} />
        </Row>
      </Sec>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════════
   TAB 3 — Шелл
══════════════════════════════════════════════════════════════════════ */
const ShellTab = ({ s, upd }) => {
  const [newApp, setNewApp] = useState({ name: '', rule: 'before' });
  const autoApps = s.autostart_apps || [];
  const tipAmounts = s.tip_amounts || [10, 30, 50, 100, 200];

  const addApp = () => {
    if (!newApp.name.trim()) return;
    upd('autostart_apps', [...autoApps, { ...newApp }]);
    setNewApp({ name: '', rule: 'before' });
  };
  const removeApp = (i) => upd('autostart_apps', autoApps.filter((_, idx) => idx !== i));

  return (
    <div>
      {/* Download */}
      <Sec title="Дистрибутив">
        <Row label="Ссылка на установщик" hint="URL, откуда клиентские ПК качают шелл (ваш хостинг/облако)">
          <Inp value={s.shell_download_url || ''} onChange={e => upd('shell_download_url', e.target.value)}
            placeholder="https://.../PCHub.User.App.exe" />
        </Row>
        <Row label="Шелл-приложение" hint="Скачать установщик для клиентских ПК" last>
          <button className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={() => {
              const url = (s.shell_download_url || '').trim();
              if (url) window.open(url, '_blank', 'noopener');
              else window.alert('Сначала укажите ссылку на установщик выше и сохраните настройки.');
            }}>
            <Download size={14} /> Скачать шелл
          </button>
        </Row>
      </Sec>

      {/* Управление питанием */}
      <Sec title="Управление питанием">
        <Row label="Действие при завершении сеанса">
          <Sel value={s.session_end_action} onChange={e => upd('session_end_action', e.target.value)} style={{ width: '200px' }}
            options={[
              { value: 'shutdown', label: 'Выключить' },
              { value: 'restart', label: 'Перезагрузить' },
              { value: 'lock', label: 'Заблокировать' },
              { value: 'nothing', label: 'Ничего не делать' },
            ]} />
        </Row>
        <Row label="Задержка (мин)" hint="Через сколько минут выполнить действие">
          <Num value={s.session_end_delay} onChange={e => upd('session_end_delay', e.target.value)} placeholder="0" />
        </Row>
        <Row label="Автовыключение при простое">
          <Tog value={s.auto_shutdown_idle} onChange={v => upd('auto_shutdown_idle', v)} label="Включено" />
        </Row>
        <Row label="Задержка автовыключения (мин)" last>
          <Num value={s.shutdown_idle_delay} onChange={e => upd('shutdown_idle_delay', e.target.value)} placeholder="30" />
        </Row>
      </Sec>

      {/* Автозапуск */}
      <Sec title="Автозапуск приложений">
        <Row label="Приложения" hint="Запускаются на клиентском ПК автоматически" last>
          <div style={{ width: '100%' }}>
            <div style={{ borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-color)', marginBottom: '10px' }}>
              {autoApps.length === 0 ? (
                <div style={{ padding: '14px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                  Нет приложений
                </div>
              ) : autoApps.map((a, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '9px 14px', borderBottom: i < autoApps.length - 1 ? '1px solid var(--border-row)' : 'none' }}>
                  <span style={{ flex: 1, fontSize: '13px' }}>{a.name}</span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)',
                    background: 'var(--hover-overlay)', borderRadius: '4px', padding: '2px 8px' }}>
                    {a.rule === 'before' ? 'До старта сеанса' : 'Работает всегда'}
                  </span>
                  <button className="icon-btn" style={{ width: '24px', height: '24px' }}
                    onClick={() => removeApp(i)}><X size={13} /></button>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <Inp value={newApp.name} onChange={e => setNewApp(p => ({ ...p, name: e.target.value }))}
                placeholder="steam.exe" style={{ flex: 1 }} />
              <Sel value={newApp.rule} onChange={e => setNewApp(p => ({ ...p, rule: e.target.value }))}
                style={{ width: '180px' }}
                options={[
                  { value: 'before', label: 'До старта сеанса' },
                  { value: 'always', label: 'Работает всегда' },
                ]} />
              <button className="btn btn-secondary" style={{ height: '36px', padding: '0 14px', fontSize: '12px' }}
                onClick={addApp}><Plus size={13} /></button>
            </div>
          </div>
        </Row>
      </Sec>

      {/* Возможности клиента */}
      <Sec title="Возможности клиента">
        <Row label="Отзывы">
          <Tog value={s.client_reviews} onChange={v => upd('client_reviews', v)} label="Включено" />
        </Row>
        <Row label="Чаевые">
          <Tog value={s.client_tips} onChange={v => upd('client_tips', v)} label="Включено" />
        </Row>
        {s.client_tips && (
          <Row label="Суммы чаевых" hint="5 вариантов для выбора клиентом">
            <div style={{ display: 'flex', gap: '8px' }}>
              {[0, 1, 2, 3, 4].map(i => (
                <Inp key={i} type="number" value={tipAmounts[i] ?? ''} placeholder={(i + 1) * 50}
                  style={{ width: '70px' }}
                  onChange={e => {
                    const arr = [...tipAmounts];
                    arr[i] = Number(e.target.value);
                    upd('tip_amounts', arr);
                  }} />
              ))}
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', alignSelf: 'center' }}>сум</span>
            </div>
          </Row>
        )}
        <Row label="Самостоятельный перевод депозита">
          <Tog value={s.self_transfer} onChange={v => upd('self_transfer', v)} label="Включено" />
        </Row>
        <Row label="Перевод между зонами">
          <Tog value={s.cross_zone_transfer} onChange={v => upd('cross_zone_transfer', v)} label="Включено" />
        </Row>
        <Row label="Перевод с активным тарифом">
          <Tog value={s.transfer_with_tariff} onChange={v => upd('transfer_with_tariff', v)} label="Включено" />
        </Row>
        <Row label="Вызов персонала">
          <Tog value={s.staff_call} onChange={v => upd('staff_call', v)} label="Включено" />
        </Row>
        <Row label="Время ответа персонала (мин)">
          <Num value={s.call_response_min} onChange={e => upd('call_response_min', e.target.value)} placeholder="3" />
        </Row>
        <Row label="Настройки звука">
          <Tog value={s.client_sound_settings} onChange={v => upd('client_sound_settings', v)} label="Доступно" />
        </Row>
        <Row label="Настройки мыши" last>
          <Tog value={s.client_mouse_settings} onChange={v => upd('client_mouse_settings', v)} label="Доступно" />
        </Row>
      </Sec>

      {/* Витрина товаров */}
      <Sec title="Витрина товаров">
        <Row label="Показывать витрину в шелле" last>
          <Tog value={s.shell_product_showcase} onChange={v => upd('shell_product_showcase', v)} label="Включено" />
        </Row>
      </Sec>

      {/* Язык и правила */}
      <Sec title="Язык и правила клуба">
        <Row label="Показывать правила клуба">
          <Tog value={s.show_club_rules} onChange={v => upd('show_club_rules', v)} label="Включено" />
        </Row>
        {s.show_club_rules && (
          <Row label="Текст правил">
            <textarea value={s.club_rules_text || ''} onChange={e => upd('club_rules_text', e.target.value)}
              rows={5} placeholder="Введите правила клуба..."
              style={{ width: '100%', background: 'var(--bg-input)', border: '1px solid var(--border-input)',
                borderRadius: '8px', color: 'var(--text-main)', fontSize: '13px',
                fontFamily: 'inherit', padding: '10px 12px', resize: 'vertical' }} />
          </Row>
        )}
        <Row label="Язык шелла" last>
          <Sel value={s.shell_language} onChange={e => upd('shell_language', e.target.value)} style={{ width: '180px' }}
            options={[
              { value: 'ru', label: 'Русский' },
              { value: 'en', label: 'English' },
              { value: 'kz', label: 'Қазақша' },
            ]} />
        </Row>
      </Sec>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════════
   TAB 4 — Безопасность
══════════════════════════════════════════════════════════════════════ */
const SecurityTab = ({ s, upd }) => {
  const [showPass, setShowPass] = useState(false);
  const [showVncPass, setShowVncPass] = useState(false);
  const [newWin, setNewWin] = useState({ name: '', cls: '' });
  const blockedWindows = s.blocked_windows || [];
  const hiddenDisks = s.hidden_disks || [];

  const addWindow = () => {
    if (!newWin.name || !newWin.cls) return;
    upd('blocked_windows', [...blockedWindows, { ...newWin }]);
    setNewWin({ name: '', cls: '' });
  };
  const removeWindow = (i) => upd('blocked_windows', blockedWindows.filter((_, idx) => idx !== i));

  const toggleDisk = (d) => {
    if (hiddenDisks.includes(d)) upd('hidden_disks', hiddenDisks.filter(x => x !== d));
    else upd('hidden_disks', [...hiddenDisks, d]);
  };

  return (
    <div>
      {/* Пароль высокого доступа */}
      <Sec title="Пароль высокого доступа">
        <Row label="Пароль" hint="Для выхода из шелл-режима на клиентских ПК" last>
          <div style={{ position: 'relative', width: '240px' }}>
            <Inp type={showPass ? 'text' : 'password'} value={s.high_access_password}
              onChange={e => upd('high_access_password', e.target.value)}
              placeholder="••••••••" style={{ paddingRight: '40px' }} />
            <button onClick={() => setShowPass(p => !p)}
              style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}>
              {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </Row>
      </Sec>

      {/* TightVNC */}
      <Sec title="TightVNC (удалённый рабочий стол)">
        <Row label="Включить TightVNC">
          <Tog value={s.vnc_enabled} onChange={v => upd('vnc_enabled', v)} label="Включено" />
        </Row>
        <Row label="Пароль VNC" last>
          <div style={{ position: 'relative', width: '240px' }}>
            <Inp type={showVncPass ? 'text' : 'password'} value={s.vnc_password}
              onChange={e => upd('vnc_password', e.target.value)}
              placeholder="••••••••" style={{ paddingRight: '40px' }} />
            <button onClick={() => setShowVncPass(p => !p)}
              style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}>
              {showVncPass ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </Row>
      </Sec>

      {/* Скрытие дисков */}
      <Sec title="Скрытие дисков">
        <Row label="Скрытые диски" hint="Выбранные диски не отображаются у клиента" last>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {['C:', 'D:', 'E:', 'F:', 'G:'].map(d => {
              const hidden = hiddenDisks.includes(d);
              return (
                <button key={d} onClick={() => toggleDisk(d)}
                  style={{ padding: '6px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: 600,
                    cursor: 'pointer', fontFamily: 'inherit',
                    background: hidden ? 'rgba(239,68,68,0.15)' : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${hidden ? '#ef4444' : 'var(--border-color)'}`,
                    color: hidden ? '#ef4444' : 'var(--text-muted)' }}>
                  {d}
                </button>
              );
            })}
          </div>
        </Row>
      </Sec>

      {/* Ограничения */}
      <Sec title="Ограничения">
        <Row label="Запрет внешних накопителей" hint="USB-флешки и HDD недоступны клиенту">
          <Tog value={s.block_external_storage} onChange={v => upd('block_external_storage', v)} label="Включено" />
        </Row>
        <Row label="Запрет скачивания в Chrome" hint="Блокировать загрузки файлов из браузера" last>
          <Tog value={s.block_chrome_downloads} onChange={v => upd('block_chrome_downloads', v)} label="Включено" />
        </Row>
      </Sec>

      {/* Блокировка окон */}
      <Sec title="Блокировка окон">
        <Row label="Заблокированные окна" hint="Окна с этими классами будут автоматически закрыты" last>
          <div style={{ width: '100%' }}>
            {blockedWindows.length > 0 && (
              <div style={{ border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden', marginBottom: '10px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 36px',
                  padding: '8px 14px', background: 'var(--hover-overlay)',
                  fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                  <span>Название</span><span>Класс</span><span />
                </div>
                {blockedWindows.map((w, i) => (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 36px',
                    padding: '9px 14px', alignItems: 'center', fontSize: '13px',
                    borderTop: '1px solid var(--border-row)' }}>
                    <span>{w.name}</span>
                    <span style={{ color: 'var(--text-muted)', fontFamily: 'monospace', fontSize: '12px' }}>{w.cls}</span>
                    <button className="icon-btn" style={{ width: '24px', height: '24px' }}
                      onClick={() => removeWindow(i)}><X size={12} /></button>
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: '8px' }}>
              <Inp value={newWin.name} onChange={e => setNewWin(p => ({ ...p, name: e.target.value }))}
                placeholder="Название" style={{ flex: 1 }} />
              <Inp value={newWin.cls} onChange={e => setNewWin(p => ({ ...p, cls: e.target.value }))}
                placeholder="WindowClass" style={{ flex: 1, fontFamily: 'monospace' }} />
              <button className="btn btn-secondary" style={{ height: '36px', padding: '0 14px', fontSize: '12px' }}
                onClick={addWindow}><Plus size={13} /></button>
            </div>
          </div>
        </Row>
      </Sec>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════════
   TAB 5 — Кастомизация
══════════════════════════════════════════════════════════════════════ */
const BACKGROUNDS = [
  { id: 'purple_space', label: 'Фиолетовый космос', bg: 'linear-gradient(135deg,#1a0533,#4a1278)' },
  { id: 'blue_neon',    label: 'Синий неон',         bg: 'linear-gradient(135deg,#001f3f,#003d7a)' },
  { id: 'dark_green',   label: 'Тёмный зелёный',     bg: 'linear-gradient(135deg,#002211,#004422)' },
  { id: 'red_ember',    label: 'Красные угли',        bg: 'linear-gradient(135deg,#1a0000,#6b0000)' },
  { id: 'grey_slate',   label: 'Серый сланец',        bg: 'linear-gradient(135deg,#1a1a2e,#16213e)' },
  { id: 'midnight',     label: 'Полночь',             bg: 'linear-gradient(135deg,#0d0d0d,#1a1a1a)' },
];

const TINT_COLORS = ['#232323', '#1a1a2e', '#0d1117', '#001f3f', '#002211', '#1a0533'];

const CustomTab = ({ s, upd }) => {
  const [bgMode, setBgMode] = useState('gallery');
  const logoInputRef = useRef();
  const bgInputRef = useRef();
  const { toast } = useToast();
  const [uploading, setUploading] = useState(null); // 'logo' | 'background' | null
  const clubId = localStorage.getItem('active_club_id');

  // Uploads a logo/background file to the backend, which stores it in MEDIA and
  // writes the absolute URL into ClubSettings.data (logo_url / shell_background_url —
  // the exact keys the C# shell reads). Then mirror the URL into local state.
  const uploadBranding = async (kind, file) => {
    if (!file) return;
    if (!clubId) { toast('Клуб не выбран', { type: 'warning' }); return; }
    if (file.size > 5 * 1024 * 1024) { toast('Файл больше 5 МБ', { type: 'warning' }); return; }
    setUploading(kind);
    try {
      const fd = new FormData();
      fd.append('kind', kind);
      fd.append('file', file);
      const res = await apiFetch(`/api/v1/clubs/${clubId}/settings/branding/`, {
        method: 'POST', body: fd, raw: true,
      });
      if (res && res.url && res.key) {
        upd(res.key, res.url);
        toast(kind === 'logo' ? 'Логотип загружен' : 'Фон загружен', { type: 'success' });
      } else {
        toast('Не удалось загрузить файл', { type: 'error' });
      }
    } catch (err) {
      toast('Ошибка загрузки файла', { type: 'error' });
    } finally {
      setUploading(null);
    }
  };

  return (
    <div>
      {/* Фон */}
      <Sec title="Фон шелла">
        <div style={{ display: 'flex', gap: '4px', marginBottom: '14px', padding: '0' }}>
          {[{ id: 'gallery', label: 'Галерея' }, { id: 'custom', label: 'Своё изображение' }, { id: 'solid', label: 'Сплошной цвет' }].map(m => (
            <button key={m.id} onClick={() => setBgMode(m.id)}
              style={{ padding: '5px 14px', borderRadius: '6px', fontSize: '12px', fontWeight: 500,
                cursor: 'pointer', fontFamily: 'inherit',
                background: bgMode === m.id ? 'var(--accent)' : 'var(--hover-overlay)',
                color: bgMode === m.id ? '#fff' : 'var(--text-muted)', border: 'none' }}>
              {m.label}
            </button>
          ))}
        </div>
        {bgMode === 'gallery' ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
            {BACKGROUNDS.map(b => (
              <button key={b.id} onClick={() => upd('shell_background', b.id)}
                style={{ height: '80px', borderRadius: '10px', background: b.bg, cursor: 'pointer',
                  border: `2px solid ${s.shell_background === b.id ? 'var(--accent)' : 'transparent'}`,
                  position: 'relative', overflow: 'hidden', transition: 'border-color 0.2s' }}>
                {s.shell_background === b.id && (
                  <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
                    justifyContent: 'center', background: 'rgba(0,0,0,0.3)' }}>
                    <span style={{ color: '#fff', fontSize: '18px' }}>✓</span>
                  </div>
                )}
                <div style={{ position: 'absolute', bottom: '6px', left: '6px', right: '6px',
                  fontSize: '10px', color: 'rgba(255,255,255,0.7)', textAlign: 'center' }}>
                  {b.label}
                </div>
              </button>
            ))}
          </div>
        ) : bgMode === 'custom' ? (
          <div style={{ padding: '16px 0' }}>
            <input type="file" accept="image/*" ref={bgInputRef} style={{ display: 'none' }}
              onChange={e => { uploadBranding('background', e.target.files?.[0]); e.target.value = ''; }} />
            <button className="btn btn-secondary" disabled={uploading === 'background'}
              style={{ display: 'flex', gap: '6px', alignItems: 'center', opacity: uploading === 'background' ? 0.6 : 1 }}
              onClick={() => bgInputRef.current?.click()}>
              <Upload size={14} /> {uploading === 'background' ? 'Загрузка…' : 'Загрузить изображение'}
            </button>
            {s.shell_background_url && (
              <img src={s.shell_background_url} alt="bg"
                style={{ marginTop: '12px', maxHeight: '120px', borderRadius: '8px', objectFit: 'cover' }} />
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 0' }}>
            <input type="color" value={s.shell_bg_color || '#1a1a2e'}
              onChange={e => upd('shell_bg_color', e.target.value)}
              style={{ width: '48px', height: '40px', borderRadius: '8px', border: '1px solid var(--border-input)',
                background: 'none', cursor: 'pointer', padding: '2px' }} />
            <Inp value={s.shell_bg_color || '#1a1a2e'} onChange={e => upd('shell_bg_color', e.target.value)}
              placeholder="#1a1a2e" style={{ width: '120px' }} />
          </div>
        )}
      </Sec>

      {/* Эффект тонирования */}
      <Sec title="Эффект тонирования">
        <Row label="Тонирование">
          <Tog value={s.tint_enabled} onChange={v => upd('tint_enabled', v)} label="Включено" />
        </Row>
        {s.tint_enabled && (
          <Row label="Цвет тонирования" last>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              {TINT_COLORS.map(c => (
                <button key={c} onClick={() => upd('tint_color', c)}
                  style={{ width: '28px', height: '28px', borderRadius: '6px', background: c, cursor: 'pointer',
                    border: `2px solid ${s.tint_color === c ? 'var(--accent)' : 'transparent'}` }} />
              ))}
              <input type="color" value={s.tint_color || '#232323'}
                onChange={e => upd('tint_color', e.target.value)}
                style={{ width: '36px', height: '28px', borderRadius: '6px', border: '1px solid var(--border-input)',
                  background: 'none', cursor: 'pointer', padding: '2px' }} />
              <Inp value={s.tint_color || '#232323'} onChange={e => upd('tint_color', e.target.value)}
                placeholder="#232323" style={{ width: '100px' }} />
            </div>
          </Row>
        )}
      </Sec>

      {/* Цветовая тема */}
      <Sec title="Цветовая тема шелла">
        <Row label="Акцентный цвет">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <input type="color" value={s.accent_color || '#7C62FF'}
              onChange={e => upd('accent_color', e.target.value)}
              style={{ width: '40px', height: '36px', borderRadius: '8px', border: '1px solid var(--border-input)',
                background: 'none', cursor: 'pointer', padding: '2px' }} />
            <Inp value={s.accent_color || '#7C62FF'} onChange={e => upd('accent_color', e.target.value)}
              placeholder="#7C62FF" style={{ width: '100px' }} />
          </div>
        </Row>
        <Row label="Дополнительный цвет" last>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <input type="color" value={s.secondary_color || '#000000'}
              onChange={e => upd('secondary_color', e.target.value)}
              style={{ width: '40px', height: '36px', borderRadius: '8px', border: '1px solid var(--border-input)',
                background: 'none', cursor: 'pointer', padding: '2px' }} />
            <Inp value={s.secondary_color || '#000000'} onChange={e => upd('secondary_color', e.target.value)}
              placeholder="#000000" style={{ width: '100px' }} />
          </div>
        </Row>
      </Sec>

      {/* Логотип */}
      <Sec title="Логотип клуба">
        <Row label="Логотип" hint="Отображается в шелле и на странице клуба" last>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {s.logo_url && (
              <img src={s.logo_url} alt="logo"
                style={{ width: '48px', height: '48px', borderRadius: '8px', objectFit: 'contain',
                  background: 'var(--hover-overlay)', padding: '4px' }} />
            )}
            <input type="file" accept="image/*" ref={logoInputRef} style={{ display: 'none' }}
              onChange={e => { uploadBranding('logo', e.target.files?.[0]); e.target.value = ''; }} />
            <button className="btn btn-secondary" disabled={uploading === 'logo'}
              style={{ display: 'flex', gap: '6px', alignItems: 'center', opacity: uploading === 'logo' ? 0.6 : 1 }}
              onClick={() => logoInputRef.current?.click()}>
              <Upload size={14} /> {uploading === 'logo' ? 'Загрузка…' : 'Загрузить логотип'}
            </button>
          </div>
        </Row>
      </Sec>

      {/* Заставка при простое */}
      <Sec title="Заставка при простое">
        <Row label="Включить заставку">
          <Tog value={s.screensaver_shell} onChange={v => upd('screensaver_shell', v)} label="Включено" />
        </Row>
        <Row label="Задержка (мин)" hint="Запустить заставку через N минут простоя" last>
          <Num value={s.screensaver_shell_delay}
            onChange={e => upd('screensaver_shell_delay', e.target.value)} placeholder="5" />
        </Row>
      </Sec>
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════════════
   TAB 6 — SmartGamer
══════════════════════════════════════════════════════════════════════ */
const SmartGamerTab = ({ s, upd }) => (
  <div>
    <Sec title="Бронирование">
      <Row label="Онлайн-бронирование">
        <Tog value={s.online_booking} onChange={v => upd('online_booking', v)} label="Включено" />
      </Row>
      <Row label="Мин. время бронирования (ч)">
        <Num value={s.booking_min_hours} onChange={e => upd('booking_min_hours', e.target.value)} placeholder="1" />
      </Row>
      <Row label="Макс. время бронирования (ч)">
        <Num value={s.booking_max_hours} onChange={e => upd('booking_max_hours', e.target.value)} placeholder="24" />
      </Row>
      <Row label="Время продолжения брони после сеанса (мин)">
        <Num value={s.post_session_booking_min} onChange={e => upd('post_session_booking_min', e.target.value)} placeholder="0" />
      </Row>
      <Row label="Самостоятельная отмена брони">
        <Tog value={s.booking_self_cancel} onChange={v => upd('booking_self_cancel', v)} label="Включено" />
      </Row>
      <Row label="Бесплатная отмена за (ч)">
        <Num value={s.booking_free_cancel_hours} onChange={e => upd('booking_free_cancel_hours', e.target.value)} placeholder="5" />
      </Row>
      <Row label="Штраф за позднюю отмену (%)">
        <Num value={s.booking_late_cancel_pct} onChange={e => upd('booking_late_cancel_pct', e.target.value)} placeholder="10" min={0} max={100} />
        <span style={{ marginLeft: '6px', fontSize: '13px', color: 'var(--text-muted)' }}>%</span>
      </Row>
      <Row label="Показывать заполненность">
        <Tog value={s.booking_show_occupancy} onChange={v => upd('booking_show_occupancy', v)} label="Включено" />
      </Row>
      <Row label="Считать минутные тарифы занятыми">
        <Tog value={s.booking_count_minute_tariffs} onChange={v => upd('booking_count_minute_tariffs', v)} label="Включено" />
      </Row>
      <Row label="Разрешить бронирование нескольких ПК" last>
        <Tog value={s.booking_multiple_pc} onChange={v => upd('booking_multiple_pc', v)} label="Включено" />
      </Row>
    </Sec>
    <Sec title="Общее">
      <Row label="Рейтинг игроков" hint="Отображать рейтинг игроков в шелле" last>
        <Tog value={s.player_rating} onChange={v => upd('player_rating', v)} label="Включено" />
      </Row>
    </Sec>
  </div>
);

/* ═══════════════════════════════════════════════════════════════════════
   TAB 7 — Интеграции
══════════════════════════════════════════════════════════════════════ */
/* DaData key input for legal tab auto-fill */
const DadataKeyRow = ({ s, upd }) => {
  const [show, setShow] = useState(false);
  return (
    <Sec title="DaData — автозаполнение по ИНН">
      <Row label="API-ключ DaData" hint="Используется для поиска организации по ИНН на вкладке «Юридические»" last>
        <div style={{ position: 'relative', width: '360px' }}>
          <Inp type={show ? 'text' : 'password'} value={s.dadata_api_key || ''}
            onChange={e => upd('dadata_api_key', e.target.value)}
            placeholder="Ваш API-ключ с dadata.ru"
            style={{ paddingRight: '40px' }} />
          <button onClick={() => setShow(p => !p)}
            style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
              background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}>
            {show ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
      </Row>
    </Sec>
  );
};

/* Telegram integration block */
const TelegramSection = ({ s, upd }) => {
  const { toast } = useToast();
  const [showToken, setShowToken] = useState(false);
  const [testing, setTesting]     = useState(false);
  const clubId = localStorage.getItem('active_club_id');
  const configured = !!(s.telegram_bot_token && s.telegram_chat_id);

  const handleTest = async () => {
    if (!clubId) { toast('Клуб не выбран', { type: 'warning' }); return; }
    if (!s.telegram_bot_token) { toast('Введите Bot Token', { type: 'warning' }); return; }
    if (!s.telegram_chat_id)   { toast('Введите Chat ID',  { type: 'warning' }); return; }
    setTesting(true);
    try {
      // Pass current values directly — no save required before testing
      const res = await apiFetch(`/api/v1/clubs/${clubId}/telegram/test/`, {
        method: 'POST',
        body: JSON.stringify({
          bot_token: s.telegram_bot_token.trim(),
          chat_id:   s.telegram_chat_id.trim(),
        }),
      });
      if (res.success) toast(res.message, { type: 'success' });
      else toast(res.error || 'Ошибка', { type: 'error' });
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast(msg || 'Ошибка отправки', { type: 'error' });
    } finally {
      setTesting(false);
    }
  };

  return (
    <Sec title="✈️ Telegram — уведомления">
      {/* Status banner */}
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', padding: '10px 0 14px',
        borderBottom: '1px solid var(--border-row)' }}>
        <div style={{ width: '10px', height: '10px', borderRadius: '50%',
          background: configured ? '#10b981' : '#6b7280', flexShrink: 0 }} />
        <span style={{ fontSize: '13px', color: configured ? '#10b981' : 'var(--text-muted)' }}>
          {configured ? 'Настроено — уведомления активны' : 'Не настроено'}
        </span>
      </div>

      {/* What gets notified */}
      <div style={{ padding: '12px 0', borderBottom: '1px solid var(--border-row)',
        fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.7 }}>
        Отправляются уведомления о: 💰 платежах · 🔓 открытии/закрытии смены · 👤 новых клиентах
      </div>

      {/* Bot token */}
      <Row label="Bot Token" hint="Получить у @BotFather в Telegram">
        <div style={{ position: 'relative', width: '100%' }}>
          <Inp type={showToken ? 'text' : 'password'}
            value={s.telegram_bot_token || ''}
            onChange={e => upd('telegram_bot_token', e.target.value)}
            placeholder="1234567890:AAF..."
            style={{ paddingRight: '40px' }} />
          <button onClick={() => setShowToken(p => !p)}
            style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)',
              background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}>
            {showToken ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
      </Row>

      {/* Chat ID */}
      <Row label="Chat ID" hint="ID канала/группы (например -1001234567890). Добавьте бота в канал как администратора">
        <Inp value={s.telegram_chat_id || ''}
          onChange={e => upd('telegram_chat_id', e.target.value)}
          placeholder="-1001234567890" style={{ maxWidth: '260px' }} />
      </Row>

      {/* How-to */}
      <Row label="Как настроить" last>
        <ol style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.8 }}>
          <li>Создайте бота через <strong>@BotFather</strong> → скопируйте токен</li>
          <li>Создайте канал или группу, добавьте бота как администратора</li>
          <li>Узнайте Chat ID через <strong>@userinfobot</strong> или API</li>
          <li>Вставьте токен и Chat ID выше, сохраните → нажмите «Тест»</li>
        </ol>
      </Row>

      {/* Test button */}
      <div style={{ paddingTop: '12px' }}>
        <button className="btn btn-secondary"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
          onClick={handleTest} disabled={testing}>
          {testing ? <RefreshCw size={13} style={{ animation: 'spin 1s linear infinite' }} /> : '📨'}
          {testing ? 'Отправка...' : 'Отправить тестовое сообщение'}
        </button>
        <span style={{ marginLeft: '10px', fontSize: '11px', color: 'var(--text-muted)' }}>
          Тест работает без предварительного сохранения
        </span>
      </div>
    </Sec>
  );
};

const IntegrationsTab = ({ s, upd }) => (
  <div>
    {/* Telegram — fully functional */}
    <TelegramSection s={s} upd={upd} />

    {/* Other integrations — coming soon */}
    <Sec title="Другие интеграции">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '12px', padding: '8px 0' }}>
        {[
          { name: 'Онлайн-СБП',    logo: '⚡', color: '#10b981' },
          { name: 'CloudPayments',  logo: '💳', color: '#3b82f6' },
          { name: 'Kaspi POS',      logo: '🏦', color: '#6b7280' },
          { name: 'Stripe',         logo: '💰', color: '#6b7280' },
        ].map(intg => (
          <div key={intg.name} style={{ background: 'var(--hover-overlay)',
            border: '1px solid var(--border-color)', borderRadius: '10px',
            padding: '16px', opacity: 0.5, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '22px' }}>{intg.logo}</span>
            <div>
              <div style={{ fontSize: '13px', fontWeight: 600 }}>{intg.name}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Скоро</div>
            </div>
          </div>
        ))}
      </div>
    </Sec>

    <DadataKeyRow s={s} upd={upd} />
  </div>
);

/* ═══════════════════════════════════════════════════════════════════════
   DEFAULT SETTINGS
══════════════════════════════════════════════════════════════════════ */
const DEFAULT_SETTINGS = {
  // Профиль клуба
  description: '',
  work_schedule: {},
  equipment_list: [],
  club_services: [],
  club_photos: [],
  // Интеграции
  telegram_bot_token: '',
  telegram_chat_id: '',
  // Юридические данные
  inn: '',
  legal_name: '',
  legal_address: '',
  ogrn: '',
  legal_email: '',
  popd_text: '',
  legal_confirmed: false,
  dadata_api_key: '',
  // Панель управления
  auto_launch_minute_tariff: false,
  auto_session: false,
  holiday_tariff: false,
  holiday_dates: [],
  end_before_booking_min: 5,
  booking_expiry_min: 15,
  show_sessions_map: true,
  block_deposit_virtual: false,
  postpayment: false,
  max_session_duration: 0,
  bonus_system: true,
  operator_bonuses: false,
  bonus_pay_tariffs: false,
  bonus_writeoff_pct: 50,
  personal_discount_auto: true,
  allow_payment_cancel: true,
  cancel_period_min: 5,
  mandatory_report: false,
  print_stock_list: false,
  operator_client_registration: true,
  currency: 'UZS',
  ui_language: 'ru',
  // Шелл
  session_end_action: 'shutdown',
  session_end_delay: 0,
  auto_shutdown_idle: false,
  shutdown_idle_delay: 30,
  autostart_apps: [],
  client_reviews: true,
  client_tips: false,
  tip_amounts: [10, 30, 50, 100, 200],
  self_transfer: false,
  cross_zone_transfer: false,
  transfer_with_tariff: false,
  staff_call: true,
  call_response_min: 3,
  client_sound_settings: true,
  client_mouse_settings: false,
  shell_product_showcase: true,
  show_club_rules: false,
  club_rules_text: '',
  shell_language: 'ru',
  // Безопасность
  high_access_password: '',
  vnc_enabled: false,
  vnc_password: '',
  hidden_disks: [],
  block_external_storage: false,
  block_chrome_downloads: false,
  blocked_windows: [],
  // Кастомизация
  shell_background: 'purple_space',
  shell_bg_color: '#1a1a2e',
  tint_enabled: false,
  tint_color: '#232323',
  accent_color: '#7C62FF',
  secondary_color: '#000000',
  logo_url: '',
  screensaver_shell: false,
  screensaver_shell_delay: 5,
  // SmartGamer
  online_booking: false,
  booking_min_hours: 1,
  booking_max_hours: 24,
  post_session_booking_min: 0,
  booking_self_cancel: true,
  booking_free_cancel_hours: 5,
  booking_late_cancel_pct: 10,
  booking_show_occupancy: true,
  booking_count_minute_tariffs: false,
  booking_multiple_pc: false,
  player_rating: false,
};

/* ═══════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
══════════════════════════════════════════════════════════════════════ */
const SettingsPage = () => {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('club');
  const [club, setClub] = useState({
    name: '', site: '', phone: '', email: '', city: '', street: '', house: '',
    country: '', contact_name: '', timezone: 'Europe/Moscow', club_token: '',
  });
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  // BUGFIX(#5): track unsaved edits so we can warn before the tab/page is closed
  // or reloaded (e.g. switching clubs triggers window.location.reload()).
  const [dirty, setDirty] = useState(false);

  const clubId = localStorage.getItem('active_club_id');

  // Load club info + operational settings from API
  const load = useCallback(async () => {
    if (!clubId) { setLoading(false); return; }
    setLoading(true);
    try {
      const [clubData, settingsData] = await Promise.all([
        apiFetch(`/api/v1/clubs/${clubId}/`).catch(() => null),
        apiFetch(`/api/v1/clubs/${clubId}/settings/`).catch(() => null),
      ]);
      if (clubData) {
        setClub({
          name:         clubData.name          || '',
          site:         clubData.site          || '',
          phone:        clubData.contact_phone || '',
          email:        settingsData?.data?.contact_email || '',
          country:      clubData.country       || '',
          city:         clubData.city          || '',
          street:       clubData.street        || '',
          house:        clubData.house         || '',
          contact_name: clubData.contact_name  || '',
          timezone:     clubData.timezone      || 'Europe/Moscow',
          club_token:   clubData.club_token    || '',
        });
      }
      if (settingsData?.data) {
        setSettings(prev => ({ ...prev, ...settingsData.data }));
      }
      setDirty(false); // freshly loaded state matches the server
    } finally {
      setLoading(false);
    }
  }, [clubId]);

  useEffect(() => { load(); }, [load]);

  // Warn before leaving with unsaved changes (close tab / reload / club switch).
  useEffect(() => {
    if (!dirty) return;
    const handler = (e) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  const updateClub = (key, val) => { setDirty(true); setClub(p => ({ ...p, [key]: val })); };
  const updateSettings = (key, val) => { setDirty(true); setSettings(p => ({ ...p, [key]: val })); };

  const save = async () => {
    if (!clubId) { toast('Клуб не выбран', { type: 'warning' }); return; }
    setSaving(true);
    try {
      await Promise.all([
        // Основные поля клуба
        apiFetch(`/api/v1/clubs/${clubId}/`, {
          method: 'PATCH',
          body: JSON.stringify({
            name:          club.name,
            site:          club.site,
            contact_phone: club.phone,
            contact_name:  club.contact_name,
            country:       club.country,
            city:          club.city,
            street:        club.street,
            house:         club.house,
            timezone:      club.timezone,
          }),
        }),
        // Операционные настройки (+ контактный email клуба — у Club нет колонки email)
        apiFetch(`/api/v1/clubs/${clubId}/settings/`, {
          method: 'PATCH',
          body: JSON.stringify({ data: { ...settings, contact_email: club.email } }),
        }),
      ]);
      setDirty(false); // saved — drop the unsaved-changes guard
      toast('Настройки сохранены', { type: 'success' });
    } catch (e) {
      const msg = e.body ? Object.values(e.body).flat().join(', ') : e.message;
      toast('Ошибка сохранения: ' + (msg || 'server error'), { type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: '0 24px', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700,
          display: 'flex', alignItems: 'center', gap: '8px' }}>
          <SettingsIcon size={20} /> Настройки
        </h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={load} disabled={loading} title="Обновить">
            <RefreshCw size={14} />
          </button>
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            <Save size={14} /> {saving ? 'Сохранение…' : 'Сохранить'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
        {/* Sidebar */}
        <div style={{ width: '190px', flexShrink: 0, position: 'sticky', top: '0' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {TABS.map(t => {
              const Icon = t.icon;
              const active = activeTab === t.id;
              return (
                <button key={t.id} onClick={() => setActiveTab(t.id)}
                  style={{ display: 'flex', alignItems: 'center', gap: '10px',
                    padding: '9px 12px', borderRadius: '8px', fontSize: '13px', fontWeight: 500,
                    cursor: 'pointer', fontFamily: 'inherit', border: 'none', textAlign: 'left',
                    background: active ? 'var(--accent-dim)' : 'transparent',
                    color: active ? 'var(--accent)' : 'var(--text-muted)',
                    transition: 'all 0.15s' }}>
                  <Icon size={15} /> {t.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {loading ? (
            <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
              Загрузка настроек…
            </div>
          ) : activeTab === 'club' ? (
            <ClubTab club={club} onChange={updateClub} s={settings} upd={updateSettings} />
          ) : activeTab === 'legal' ? (
            <LegalTab s={settings} upd={updateSettings} />
          ) : activeTab === 'panel' ? (
            <PanelTab s={settings} upd={updateSettings} />
          ) : activeTab === 'shell' ? (
            <ShellTab s={settings} upd={updateSettings} />
          ) : activeTab === 'security' ? (
            <SecurityTab s={settings} upd={updateSettings} />
          ) : activeTab === 'custom' ? (
            <CustomTab s={settings} upd={updateSettings} />
          ) : activeTab === 'smartgamer' ? (
            <SmartGamerTab s={settings} upd={updateSettings} />
          ) : (
            <IntegrationsTab s={settings} upd={updateSettings} />
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
