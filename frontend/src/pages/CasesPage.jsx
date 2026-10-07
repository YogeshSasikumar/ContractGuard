import { useState, useEffect } from 'react';
import axios from 'axios';
import { Scale, Calendar, DollarSign, BookOpen, AlertTriangle, Filter } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function CasesPage() {
  const [cases, setCases] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [expandedCase, setExpandedCase] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/cases/`);
      setCases(res.data.cases || []);
    } catch (err) {
      // Fallback: load from embedded data if API is down
      console.warn('API unavailable, using embedded case data');
      setCases([]);
    } finally {
      setLoading(false);
    }
  };

  const filtered = cases.filter(c => {
    if (filter === 'ALL') return true;
    return c.risk_level === filter;
  });

  return (
    <>
      <div className="page-header">
        <h2>Case Studies</h2>
        <p>Real legal cases showing the impact of risky contract clauses</p>
      </div>

      <div className="page-body">
        {/* Filter Bar */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          marginBottom: '24px',
          padding: '12px 16px',
          background: 'var(--bg-card)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-subtle)',
        }}>
          <Filter size={16} color="var(--text-muted)" />
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Filter:</span>
          {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map(level => (
            <button
              key={level}
              className={`btn btn-ghost`}
              onClick={() => setFilter(level)}
              style={{
                padding: '6px 14px',
                fontSize: '12px',
                borderRadius: '20px',
                background: filter === level ? (level === 'ALL' ? 'rgba(99,102,241,0.12)' : level === 'HIGH' ? 'var(--risk-high-bg)' : level === 'MEDIUM' ? 'var(--risk-medium-bg)' : 'var(--risk-low-bg)') : 'transparent',
                color: filter === level ? (level === 'ALL' ? 'var(--accent-secondary)' : level === 'HIGH' ? 'var(--risk-high)' : level === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)') : 'var(--text-muted)',
                border: filter === level ? '1px solid currentColor' : '1px solid transparent',
              }}
            >
              {level === 'ALL' ? `All (${cases.length})` : `${level} (${cases.filter(c => c.risk_level === level).length})`}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="loading-container">
            <div className="loading-spinner" />
            <p className="loading-text">Loading case studies...</p>
          </div>
        ) : (
          <div className="case-grid">
            {filtered.map(caseItem => (
              <div 
                key={caseItem.id} 
                className="case-card"
                onClick={() => setExpandedCase(expandedCase === caseItem.id ? null : caseItem.id)}
                style={{ cursor: 'pointer' }}
                id={`case-${caseItem.id}`}
              >
                <div className="case-card-header">
                  <div>
                    <h3>{caseItem.case_name}</h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
                      <span className={`risk-badge ${caseItem.risk_level?.toLowerCase()}`}>
                        {caseItem.clause_type}
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Calendar size={12} /> {caseItem.year}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="case-card-body">
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    <strong style={{ color: 'var(--text-secondary)' }}>{caseItem.parties}</strong>
                  </p>
                  <p>{expandedCase === caseItem.id ? caseItem.summary : caseItem.summary?.substring(0, 150) + '...'}</p>
                  
                  {expandedCase === caseItem.id && (
                    <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div style={{
                        padding: '12px',
                        background: 'var(--risk-high-bg)',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid rgba(239, 68, 68, 0.15)',
                      }}>
                        <p style={{ fontSize: '12px', fontWeight: 600, color: 'var(--risk-high)', marginBottom: '4px' }}>
                          <Scale size={12} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Outcome
                        </p>
                        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                          {caseItem.outcome}
                        </p>
                      </div>

                      <div style={{
                        padding: '12px',
                        background: 'rgba(99, 102, 241, 0.06)',
                        borderRadius: 'var(--radius-sm)',
                        border: '1px solid rgba(99, 102, 241, 0.15)',
                      }}>
                        <p style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent-secondary)', marginBottom: '4px' }}>
                          <BookOpen size={12} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Lesson
                        </p>
                        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                          {caseItem.lesson}
                        </p>
                      </div>

                      {caseItem.source && (
                        <p style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          📚 {caseItem.source}
                        </p>
                      )}
                    </div>
                  )}
                </div>

                <div className="case-card-footer">
                  {caseItem.financial_impact && (
                    <span className="case-impact">
                      <DollarSign size={14} style={{ verticalAlign: 'middle' }} />
                      {caseItem.financial_impact}
                    </span>
                  )}
                  <span style={{ fontSize: '12px', color: 'var(--accent-secondary)' }}>
                    {expandedCase === caseItem.id ? 'Click to collapse' : 'Click for details'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div style={{ 
            textAlign: 'center', 
            padding: '60px 40px', 
            color: 'var(--text-muted)' 
          }}>
            <AlertTriangle size={40} style={{ marginBottom: '16px', opacity: 0.5 }} />
            <p>No cases found with the current filter.</p>
          </div>
        )}
      </div>
    </>
  );
}
