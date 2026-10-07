import { NavLink } from 'react-router-dom';
import { Shield, Upload, BookOpen, History, BarChart3 } from 'lucide-react';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">
          <Shield size={22} color="white" />
        </div>
        <h1>Riskora</h1>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/analyze" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Upload className="nav-icon" size={20} />
          Analyze Contract
        </NavLink>

        <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <History className="nav-icon" size={20} />
          Previous Analyses
        </NavLink>

        <NavLink to="/comparison" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <BarChart3 className="nav-icon" size={20} />
          Model Comparison
        </NavLink>

        <NavLink to="/cases" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <BookOpen className="nav-icon" size={20} />
          Case Studies
        </NavLink>
      </nav>

      <div style={{ padding: '16px 12px', borderTop: '1px solid var(--border-subtle)' }}>
        <div style={{
          padding: '16px',
          background: 'rgba(99, 102, 241, 0.06)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid rgba(99, 102, 241, 0.12)'
        }}>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>Powered by</p>
          <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--accent-secondary)' }}>Legal-BERT + Gemini Pro</p>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>CCRAG Pipeline v2.0</p>
        </div>
      </div>
    </aside>
  );
}
