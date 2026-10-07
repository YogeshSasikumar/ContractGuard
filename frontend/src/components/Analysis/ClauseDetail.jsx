import { X, AlertTriangle, AlertCircle, CheckCircle, BookOpen, PenTool, Lightbulb, ShieldAlert, Scale } from 'lucide-react';

const RISK_ICONS = {
  HIGH: <AlertTriangle size={18} color="#ef4444" />,
  MEDIUM: <AlertCircle size={18} color="#f59e0b" />,
  LOW: <CheckCircle size={18} color="#10b981" />,
};

export default function ClauseDetail({ clause, onClose }) {
  if (!clause) return null;

  return (
    <>
      <div className="detail-panel-overlay" onClick={onClose} />
      <div className="detail-panel">
        <div className="detail-panel-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {RISK_ICONS[clause.risk_level]}
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 600 }}>{clause.clause_type}</h3>
              <span className={`risk-badge ${clause.risk_level.toLowerCase()}`} style={{ marginTop: '4px' }}>
                {clause.risk_level} RISK · {Math.round(clause.confidence * 100)}% confidence
              </span>
            </div>
          </div>
          <button className="btn btn-ghost" onClick={onClose} style={{ padding: '8px' }}>
            <X size={20} />
          </button>
        </div>

        <div className="detail-panel-body">
          {/* Original Clause Text */}
          <div className="detail-section">
            <h4>
              <BookOpen size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
              Original Clause Text
            </h4>
            <div className="clause-full-text">
              {clause.text}
            </div>
            {clause.page_number && (
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
                📄 Page {clause.page_number} {clause.section_heading && `· § ${clause.section_heading}`}
              </p>
            )}
          </div>

          {/* Model Intelligence */}
          {(clause.model_used || clause.centrality != null) && (
            <div className="detail-section">
              <h4>🤖 Model Intelligence</h4>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '12px',
              }}>
                {clause.model_used && (
                  <div style={{
                    padding: '12px',
                    background: 'rgba(99, 102, 241, 0.06)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid rgba(99, 102, 241, 0.12)',
                    textAlign: 'center',
                  }}>
                    <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Classified By</p>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--accent-secondary)', textTransform: 'uppercase' }}>
                      {clause.model_used}
                    </p>
                  </div>
                )}
                {clause.centrality != null && (
                  <div style={{
                    padding: '12px',
                    background: 'rgba(99, 102, 241, 0.06)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid rgba(99, 102, 241, 0.12)',
                    textAlign: 'center',
                  }}>
                    <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Graph Centrality</p>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {(clause.centrality * 100).toFixed(1)}%
                    </p>
                  </div>
                )}
                {clause.risk_score != null && (
                  <div style={{
                    padding: '12px',
                    background: 'rgba(99, 102, 241, 0.06)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid rgba(99, 102, 241, 0.12)',
                    textAlign: 'center',
                  }}>
                    <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>Risk Score</p>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--risk-high)' }}>
                      {(clause.risk_score * 100).toFixed(1)}%
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* AI Explanation */}
          {clause.explanation && (
            <div className="detail-section">
              <h4>
                <Lightbulb size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                AI Explanation
              </h4>
              <div className="content">
                {clause.explanation}
              </div>
            </div>
          )}

          {/* Risks */}
          {clause.risks && clause.risks.length > 0 && (
            <div className="detail-section">
              <h4>
                <ShieldAlert size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                Key Risks
              </h4>
              <ul style={{ 
                listStyle: 'none', 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '8px' 
              }}>
                {clause.risks.map((risk, i) => (
                  <li key={i} style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    fontSize: '13px',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.6,
                    padding: '10px 14px',
                    background: 'var(--risk-high-bg)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid rgba(239, 68, 68, 0.1)',
                  }}>
                    <AlertTriangle size={14} color="#ef4444" style={{ flexShrink: 0, marginTop: '2px' }} />
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommendations */}
          {clause.recommendations && clause.recommendations.length > 0 && (
            <div className="detail-section">
              <h4>💡 Recommendations</h4>
              <ul style={{ 
                listStyle: 'none', 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '8px' 
              }}>
                {clause.recommendations.map((rec, i) => (
                  <li key={i} style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                    fontSize: '13px',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.6,
                    padding: '10px 14px',
                    background: 'rgba(99, 102, 241, 0.06)',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid rgba(99, 102, 241, 0.1)',
                  }}>
                    <Lightbulb size={14} color="var(--accent-secondary)" style={{ flexShrink: 0, marginTop: '2px' }} />
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Rewrite */}
          {clause.suggested_rewrite && (
            <div className="detail-section">
              <h4>
                <PenTool size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                Suggested Rewrite
              </h4>
              <div className="rewrite-box">
                {clause.suggested_rewrite}
              </div>
            </div>
          )}

          {/* Related Cases */}
          {clause.related_cases && clause.related_cases.length > 0 && (
            <div className="detail-section">
              <h4>⚖️ Related Legal Cases</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {clause.related_cases.map((caseItem, i) => (
                  <div key={i} style={{
                    padding: '16px',
                    background: 'var(--bg-primary)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                      <h5 style={{ fontSize: '14px', fontWeight: 600, flex: 1 }}>
                        {caseItem.case_name} {caseItem.year ? `(${caseItem.year})` : ''}
                      </h5>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        {caseItem.similarity_score != null && (
                          <span style={{
                            fontSize: '10px',
                            padding: '2px 8px',
                            borderRadius: '10px',
                            background: 'rgba(99, 102, 241, 0.12)',
                            color: 'var(--accent-secondary)',
                            fontWeight: 600,
                          }}>
                            {(caseItem.similarity_score * 100).toFixed(0)}% match
                          </span>
                        )}
                        {caseItem.risk_level && (
                          <span className={`risk-badge ${caseItem.risk_level?.toLowerCase()}`} style={{ fontSize: '10px', padding: '2px 8px' }}>
                            {caseItem.risk_level}
                          </span>
                        )}
                      </div>
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '8px' }}>
                      {caseItem.summary?.substring(0, 200)}{caseItem.summary?.length > 200 ? '...' : ''}
                    </p>
                    {caseItem.financial_impact && (
                      <p style={{ fontSize: '12px', color: 'var(--risk-high)', fontWeight: 600 }}>
                        💰 {caseItem.financial_impact}
                      </p>
                    )}
                    {caseItem.lesson && (
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px', lineHeight: 1.5, fontStyle: 'italic' }}>
                        📘 {caseItem.lesson.substring(0, 150)}{caseItem.lesson.length > 150 ? '...' : ''}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
