import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import PlatformRoot from './platform/PlatformRoot.jsx'
import './index.css'
import { ToastProvider } from './components/Toast';

// URL-based separation: /platform → SaaS operator panel, / → club panel
const isPlatform = window.location.pathname.startsWith('/platform');

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error("React Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', background: '#222', color: 'red', minHeight: '100vh', fontFamily: 'monospace' }}>
          <h2>Упс, React приложение упало</h2>
          <p>{this.state.error && this.state.error.toString()}</p>
          <pre>{this.state.errorInfo && this.state.errorInfo.componentStack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ToastProvider>
        {isPlatform ? <PlatformRoot /> : <App />}
      </ToastProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
