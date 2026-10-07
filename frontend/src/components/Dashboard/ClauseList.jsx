import { useState } from 'react';
import { AlertTriangle, AlertCircle, CheckCircle, ChevronRight, FileText, Percent, Activity } from 'lucide-react';

const RISK_ICONS = {
  HIGH: <AlertTriangle size={16} color="#ef4444" />,
  MEDIUM: <AlertCircle size={16} color="#f59e0b" />,
  LOW: <CheckCircle size={16} color="#10b981" />,
};

const RISK_COLORS = {
  HIGH: '#ef4444',
  MEDIUM: '#f59e0b',
  LOW: '#10b981',
};

export default function ClauseList({ clauses, onSelectClause }) {
  const [filter, setFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('risk_score');

  const filtered = clauses.filter(c => {
    if (filter === 'ALL') return true;
    return c.risk_level === filter;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === 'risk_score') return (b.risk_score ?? 0) - (a.risk_score ?? 0);
    if (sortBy === 'risk') {
      const order = { HIGH: 0, MEDIUM: 1, LOW: 2 };
      return (order[a.risk_level] ?? 3) - (order[b.risk_level] ?? 3);
    }
    if (sortBy === 'confidence') return b.confidence - a.confidence;
    if (sortBy === 'page') return (a.page_number ?? 999) - (b.page_number ?? 999);
    return 0;
  });

  return (
    <div className="card">
      <div className="card-header">
        <h3>📋 Clause Analysis</h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {/* Sort selector */}
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            style={{
              background: 'var(--bg-primary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '4px 10px',
              fontSize: '11px',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
            }}
          >
            <option value="risk_score">Sort: Risk Score</option>
            <option value="risk">Sort: Risk Level</option>
            <option value="confidence">Sort: Confidence</option>
            <option value="page">Sort: Page</option>
          </select>
          <span style={{ width: '1px', height: '16px', background: 'var(--border-subtle)' }} />
          {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map(level => (
            <button
              key={level}
              className={`btn btn-ghost ${filter === level ? 'active' : ''}`}
              onClick={() => setFilter(level)}
              style={{
                padding: '4px 12px',
                fontSize: '12px',
                borderRadius: '20px',
                background: filter === level ? (level === 'ALL' ? 'rgba(99,102,241,0.12)' : `${RISK_COLORS[level]}20`) : 'transparent',
                color: filter === level ? (level === 'ALL' ? 'var(--accent-secondary)' : RISK_COLORS[level]) : 'var(--text-muted)',
                border: filter === level ? `1px solid ${level === 'ALL' ? 'rgba(99,102,241,0.3)' : `${RISK_COLORS[level]}40`}` : '1px solid transparent',
              }}
            >
              {level === 'ALL' ? 'All' : level}
            </button>
          ))}
        </div>
      </div>
      
      <div className="card-body" style={{ padding: '12px' }}>
        <div className="clause-list">
          {sorted.map(clause => (
            <div
              key={clause.id}
              className={`clause-item ${clause.risk_level.toLowerCase()}`}
              onClick={() => onSelectClause(clause)}
              id={`clause-${clause.id}`}
            >
              <div className="clause-item-header">
                <h4>
                  {RISK_ICONS[clause.risk_level]}
                  {clause.clause_type}
                </h4>
                <span className={`risk-badge ${clause.risk_level.toLowerCase()}`}>
                  {clause.risk_level}
                </span>
              </div>
              
              <p className="clause-text">{clause.text}</p>
              
              <div className="clause-meta">
                {clause.page_number && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <FileText size={12} /> Page {clause.page_number}
                  </span>
                )}
                {clause.section_heading && (
                  <span>§ {clause.section_heading}</span>
                )}
                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Percent size={12} />
                  {Math.round(clause.confidence * 100)}% conf
                </span>
                {clause.risk_score != null && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: RISK_COLORS[clause.risk_level], fontWeight: 600 }}>
                    <Activity size={12} />
                    {(clause.risk_score * 100).toFixed(0)}% risk
                  </span>
                )}
                {clause.model_used && (
                  <span style={{
                    fontSize: '10px',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: clause.model_used === 'legal-bert' ? 'rgba(99,102,241,0.15)' : clause.model_used === 'bart-mnli' ? 'rgba(245,158,11,0.15)' : 'rgba(148,163,184,0.15)',
                    color: clause.model_used === 'legal-bert' ? 'var(--accent-secondary)' : clause.model_used === 'bart-mnli' ? 'var(--risk-medium)' : 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                  }}>
                    {clause.model_used}
                  </span>
                )}
                <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div className="confidence-bar">
                    <div 
                      className="fill" 
                      style={{ 
                        width: `${clause.confidence * 100}%`,
                        background: RISK_COLORS[clause.risk_level] 
                      }} 
                    />
                  </div>
                  <ChevronRight size={14} color="var(--text-muted)" />
                </div>
              </div>
            </div>
          ))}
          
          {sorted.length === 0 && (
            <div style={{ 
              padding: '40px', 
              textAlign: 'center', 
              color: 'var(--text-muted)', 
              fontSize: '14px' 
            }}>
              No clauses match the current filter.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
