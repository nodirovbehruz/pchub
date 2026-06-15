import { useState, useEffect, useCallback, useRef } from 'react';
import { MessageCircle, Send, Monitor, RefreshCw } from 'lucide-react';
import { apiFetch } from '../api/client';
import { useToast } from '../components/Toast';

const fmtTime = (s) => s ? new Date(s).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '';

const Chat = () => {
  const { toast } = useToast();
  const clubId = localStorage.getItem('active_club_id');
  const [threads, setThreads] = useState([]);
  const [active, setActive] = useState(null);      // computer_id
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const threadsTimer = useRef(null);
  const msgTimer = useRef(null);
  const scrollRef = useRef(null);
  const activeRef = useRef(null);
  useEffect(() => { activeRef.current = active; }, [active]);

  const loadThreads = useCallback(async () => {
    if (!clubId) return;
    try {
      const data = await apiFetch(`/api/v1/computers/admin/chat/?club=${clubId}`, { noCache: true });
      setThreads(Array.isArray(data) ? data : []);
    } catch { /* keep */ }
  }, [clubId]);

  const loadMessages = useCallback(async (cid) => {
    if (!cid) return;
    try {
      const data = await apiFetch(`/api/v1/computers/admin/chat/${cid}/`, { noCache: true });
      setMessages(Array.isArray(data) ? data : []);
    } catch { /* keep */ }
  }, []);

  // Threads list polls every 5s.
  useEffect(() => {
    loadThreads();
    threadsTimer.current = setInterval(loadThreads, 5000);
    return () => clearInterval(threadsTimer.current);
  }, [loadThreads]);

  // Open thread polls every 3s.
  useEffect(() => {
    if (!active) return;
    loadMessages(active);
    msgTimer.current = setInterval(() => loadMessages(active), 3000);
    return () => clearInterval(msgTimer.current);
  }, [active, loadMessages]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  // Realtime: listen for incoming client messages over WebSocket (instant, no wait).
  // Polling above stays as a fallback if the socket drops.
  useEffect(() => {
    if (!clubId) return undefined;
    const token = localStorage.getItem('access_token');
    if (!token) return undefined;
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    let ws;
    try {
      ws = new WebSocket(`${proto}://${window.location.host}/ws/client/?token=${token}&club=${clubId}`);
    } catch { return undefined; }
    ws.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data);
        if (d.type === 'chat_inbox') {
          loadThreads();
          if (activeRef.current && String(activeRef.current) === String(d.computer_id)) {
            loadMessages(d.computer_id);
          }
        }
      } catch { /* ignore */ }
    };
    return () => { try { ws.close(); } catch { /* noop */ } };
  }, [clubId, loadThreads, loadMessages]);

  const openThread = (cid) => {
    setActive(cid);
    setThreads(ts => ts.map(t => t.computer_id === cid ? { ...t, unread: 0 } : t));
  };

  const send = async () => {
    const t = text.trim();
    if (!t || !active) return;
    setSending(true);
    try {
      const msg = await apiFetch(`/api/v1/computers/admin/chat/${active}/`, {
        method: 'POST', body: JSON.stringify({ text: t }),
      });
      setMessages(m => [...m, msg]);
      setText('');
      loadThreads();
    } catch (e) {
      toast(e.body?.error || e.message || 'Ошибка', { type: 'error' });
    } finally { setSending(false); }
  };

  const activeThread = threads.find(t => t.computer_id === active);

  return (
    <div style={{ padding: '20px 24px', height: 'calc(100vh - 90px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <MessageCircle size={22} />
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>Чат с клиентами</h1>
        <button className="btn btn-secondary" style={{ fontSize: 12, marginLeft: 'auto' }} onClick={loadThreads}>
          <RefreshCw size={13} /> Обновить
        </button>
      </div>

      <div style={{ flex: 1, display: 'flex', gap: 14, minHeight: 0 }}>
        {/* Threads */}
        <div style={{ width: 300, flexShrink: 0, background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
          borderRadius: 12, overflowY: 'auto' }}>
          {threads.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Сообщений пока нет</div>
          ) : threads.map(t => (
            <div key={t.computer_id} onClick={() => openThread(t.computer_id)}
              style={{ padding: '12px 14px', cursor: 'pointer', borderBottom: '1px solid var(--border-color)',
                background: active === t.computer_id ? 'var(--hover-overlay)' : 'transparent',
                borderLeft: active === t.computer_id ? '3px solid #6366f1' : '3px solid transparent' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, fontSize: 13 }}>
                  <Monitor size={13} /> {t.computer_name}
                </div>
                {t.unread > 0 && (
                  <span style={{ background: '#f59e0b', color: '#000', fontSize: 11, fontWeight: 700,
                    padding: '1px 7px', borderRadius: 999 }}>{t.unread}</span>
                )}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.last_text}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{fmtTime(t.last_at)}</div>
            </div>
          ))}
        </div>

        {/* Messages */}
        <div style={{ flex: 1, background: 'var(--bg-panel)', border: '1px solid var(--border-color)',
          borderRadius: 12, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          {!active ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              Выберите чат слева
            </div>
          ) : (
            <>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-color)', fontWeight: 600 }}>
                {activeThread?.computer_name || `ПК #${active}`}
              </div>
              <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {messages.map(m => (
                  <div key={m.id} style={{ alignSelf: m.from_admin ? 'flex-end' : 'flex-start', maxWidth: '70%' }}>
                    <div style={{ padding: '8px 12px', borderRadius: 10, fontSize: 13,
                      background: m.from_admin ? '#6366f1' : 'var(--bg-dark)',
                      color: m.from_admin ? '#fff' : 'var(--text-main)' }}>{m.text}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2,
                      textAlign: m.from_admin ? 'right' : 'left' }}>
                      {m.from_admin ? (m.sender_name || 'Оператор') : (m.sender_name || 'Гость')} · {fmtTime(m.created_at)}
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ padding: 12, borderTop: '1px solid var(--border-color)', display: 'flex', gap: 8 }}>
                <input value={text} onChange={e => setText(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') send(); }}
                  placeholder="Сообщение клиенту…"
                  style={{ flex: 1, height: 40, padding: '0 14px', background: 'var(--bg-dark)',
                    border: '1px solid var(--border-color)', borderRadius: 10, color: 'var(--text-main)', fontSize: 14 }} />
                <button className="btn btn-primary" onClick={send} disabled={sending || !text.trim()}>
                  <Send size={15} />
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Chat;
