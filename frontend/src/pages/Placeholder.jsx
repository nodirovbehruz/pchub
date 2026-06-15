const Placeholder = ({ title, icon: Icon, message }) => (
  <div style={{ padding: '0 24px' }}>
    <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '20px' }}>{title}</h2>
    <div
      className="glass-panel"
      style={{
        textAlign: 'center',
        padding: '60px 40px',
        color: 'var(--text-muted)',
        borderRadius: '14px',
      }}
    >
      {Icon && (
        <Icon
          size={40}
          style={{ opacity: 0.3, display: 'block', margin: '0 auto 12px' }}
        />
      )}
      <div style={{ fontSize: '14px' }}>
        {message || 'Раздел находится в разработке'}
      </div>
      <div style={{ fontSize: '11px', opacity: 0.6, marginTop: '8px' }}>
        Backend модели готовы, скоро будет UI
      </div>
    </div>
  </div>
);

export default Placeholder;
