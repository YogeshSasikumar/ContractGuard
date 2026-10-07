import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Clock, FileText, AlertTriangle, AlertCircle, CheckCircle, ArrowRight, Loader2, FolderOpen } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STORAGE_KEY = 'riskora_analysis';

const RISK_COLORS = { HIGH: '#ef4444', MEDIUM: '#f59e0b', LOW: '#10b981' };

export default function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingId, setLoadingId] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/history`, { timeout: 10000 });
      setHistory(res.data.analyses || []);
    } catch (e) {
      console.error('Failed to load history:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadAnalysis = useCallback(async (jobId) => {
    setLoadingId(jobId);
    try {
      const res = await axios.get(`${API_URL}/api/analysis/${jobId}`, { timeout: 10000 });
      // Store in localStorage so AnalysisPage picks it up instantly
      localStorage.setItem(STORAGE_KEY, JSON.stringify(res.data));
      navigate('/analyze');
    } catch (e) {
      console.error('Failed to load analysis:', e);
      setLoadingId(null);
    }
  }, [navigate]);

  const getRiskBadge = (score) => {
    if (score >= 60) return { level: 'HIGH', color: RISK_COLORS.HIGH };
    if (score >= 30) return { level: 'MEDIUM', color: RISK_COLORS.MEDIUM };
    return { level: 'LOW', color: RISK_COLORS.LOW };
  };

  return (
    <>
      <div className="page-header">
        <h2>Previous Analyses</h2>
        <p>Instantly load results from previously analyzed contracts</p>
      </div>

      <div className="page-body">
        {loading && (
          <div className="loading-container" style={{ minHeight: '200px' }}>
            <div className="loading-spinner" />
            <p className="loading-text">Loading history...</p>
          </div>
        )}

        {!loading && history.length === 0 && (
          <div style={{
            padding: '60px 40px',
            textAlign: 'center',
            background: 'var(--bg-card)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-subtle)',
          }}>
            <FolderOpen size={48} color="var(--text-muted)" style={{ marginBottom: '16px' }} />
            <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>No Previous Analyses</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>
              Upload a contract on the Analyze page to get started.
            </p>
            <button className="btn btn-primary" onClick={() => navigate('/analyze')}>
              <FileText size={16} /> Analyze Contract
            </button>
          </div>
        )}

        {!loading && history.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {history.map((item) => {
              const badge = getRiskBadge(item.overall_risk_score);
              const isLoading = loadingId === item.job_id;
              return (
                <div
                  key={item.job_id}
                  className="history-card"
                  onClick={() => !isLoading && loadAnalysis(item.job_id)}
                >
                  <div className="history-card-left">
                    <div className="history-icon" style={{ background: `${badge.color}15`, color: badge.color }}>
                      <FileText size={20} />
                    </div>
                    <div>
                      <h4 className="history-name">{item.document_name}</h4>
                      <div className="history-meta">
                        <span>{item.total_pages} pages</span>
                        <span>·</span>
                        <span>{item.total_clauses} clauses</span>
                        <span>·</span>
                        <span>{item.processing_time}s</span>
                      </div>
                    </div>
                  </div>

                  <div className="history-card-right">
                    <div className="history-risks">
                      {item.high_risk > 0 && (
                        <span className="history-risk-count high">
                          <AlertTriangle size={12} /> {item.high_risk}
                        </span>
                      )}
                      {item.medium_risk > 0 && (
                        <span className="history-risk-count medium">
                          <AlertCircle size={12} /> {item.medium_risk}
                        </span>
                      )}
                      {item.low_risk > 0 && (
                        <span className="history-risk-count low">
                          <CheckCircle size={12} /> {item.low_risk}
                        </span>
                      )}
                    </div>

                    <div className="history-score" style={{ color: badge.color }}>
                      {Math.round(item.overall_risk_score)}
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'block' }}>risk</span>
                    </div>

                    <div className="history-action">
                      {isLoading ? (
                        <Loader2 size={18} className="animate-spin" style={{ color: 'var(--accent-secondary)' }} />
                      ) : (
                        <ArrowRight size={18} color="var(--text-muted)" />
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
