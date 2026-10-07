import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { Shield, AlertTriangle, AlertCircle, CheckCircle, Clock, FileText, Scan, Brain, Lightbulb, Check, Network, Scale, Activity, Trash2, Info } from 'lucide-react';
import UploadZone from '../components/Upload/UploadZone';
import RiskOverview from '../components/Dashboard/RiskOverview';
import ClauseList from '../components/Dashboard/ClauseList';
import ClauseDetail from '../components/Analysis/ClauseDetail';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const STORAGE_KEY = 'riskora_analysis';
const POLL_INTERVAL_MS = 2500;

const STEP_MAP = {
  'Extracting text from PDF...': 0,
  'Segmenting clauses...': 1,
  'Classifying': 2,
  'Building clause': 3,
  'Matching case': 4,
  'Generating AI': 5,
  'Finalizing': 5,
  'Analysis complete': 5,
};

const LOADING_STEPS = [
  { icon: FileText, label: 'Extracting text from PDF...' },
  { icon: Scan, label: 'Segmenting clauses...' },
  { icon: Brain, label: 'Classifying clauses (ML)...' },
  { icon: Network, label: 'Building clause graph...' },
  { icon: Scale, label: 'Matching case law...' },
  { icon: Lightbulb, label: 'Generating AI explanations...' },
];

const MODEL_LABELS = {
  legal_bert: { name: 'Legal-BERT', color: '#6366f1' },
  bart_mnli: { name: 'BART-MNLI', color: '#f59e0b' },
  sentence_transformer: { name: 'MiniLM', color: '#10b981' },
  gemini_available: { name: 'Gemini', color: '#8b5cf6' },
};

function getStepIndex(stepText) {
  if (!stepText) return 0;
  for (const [key, idx] of Object.entries(STEP_MAP)) {
    if (stepText.includes(key) || stepText.toLowerCase().includes(key.toLowerCase())) {
      return idx;
    }
  }
  return 0;
}

export default function AnalysisPage() {
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [selectedClause, setSelectedClause] = useState(null);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  // Restore from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed && parsed.clauses && parsed.clauses.length > 0) {
          setAnalysisResult(parsed);
        }
      }
    } catch (e) {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  // Save to localStorage when result changes
  useEffect(() => {
    if (analysisResult) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(analysisResult));
      } catch (e) { /* quota exceeded — ignore */ }
    }
  }, [analysisResult]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const clearAnalysis = useCallback(() => {
    setAnalysisResult(null);
    setSelectedClause(null);
    setError(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const pollStatus = useCallback((jobId) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await axios.get(`${API_URL}/api/status/${jobId}`, { timeout: 10000 });
        const data = res.data;

        // Update progress
        setProgress(data.progress || 0);
        setLoadingStep(getStepIndex(data.step));

        if (data.status === 'completed' && data.result) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setAnalysisResult(data.result);
          setIsUploading(false);
        } else if (data.status === 'failed') {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setError(data.error || 'Analysis failed.');
          setIsUploading(false);
        }
      } catch (err) {
        // Network error during polling — keep trying
        console.warn('Poll error (retrying):', err.message);
      }
    }, POLL_INTERVAL_MS);
  }, []);

  const handleUpload = async (file) => {
    setIsUploading(true);
    setError(null);
    setAnalysisResult(null);
    setLoadingStep(0);
    setProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Upload returns immediately with job_id
      const response = await axios.post(`${API_URL}/api/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000, // 120s for large file uploads
        maxContentLength: Infinity,
        maxBodyLength: Infinity,
      });

      const jobId = response.data.job_id;
      if (!jobId) throw new Error('No job ID returned');

      // Start polling for results
      pollStatus(jobId);

    } catch (err) {
      let message = 'Upload failed.';
      if (err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
        message = 'Cannot connect to backend server. Make sure the backend is running on port 8000.';
      } else if (err.code === 'ECONNABORTED') {
        message = 'Upload timed out. The file may be too large — try a smaller document.';
      } else if (err.response?.data?.detail) {
        message = err.response.data.detail;
      } else if (err.message) {
        message = err.message;
      }
      setError(message);
      setIsUploading(false);
    }
  };

  const topRiskyClauses = analysisResult?.risk_summary?.top_risky_clauses || [];
  const graphStats = analysisResult?.risk_summary?.graph_stats;
  const modelHealth = analysisResult?.model_health;
  const novelty = analysisResult?.system_novelty;

  return (
    <>
      <div className="page-header">
        <h2>Contract Analysis</h2>
        <p>Upload a PDF contract to identify and assess risky clauses</p>
      </div>

      <div className="page-body">
        {/* Upload Zone */}
        {!analysisResult && !isUploading && (
          <UploadZone onUpload={handleUpload} isUploading={isUploading} />
        )}

        {/* Error */}
        {error && (
          <div className="error-banner">
            <AlertTriangle size={20} />
            <div>
              <strong>Analysis Error</strong>
              <p style={{ marginTop: '4px', color: 'var(--text-secondary)' }}>{error}</p>
              <button className="btn btn-ghost" style={{ marginTop: '8px', fontSize: '12px' }} onClick={() => { setError(null); }}>
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Loading — shows real progress from backend */}
        {isUploading && (
          <div className="loading-container">
            <div className="loading-spinner" />
            <h3 style={{ fontSize: '18px', fontWeight: 600 }}>Analyzing your contract...</h3>

            {/* Progress bar */}
            <div style={{ width: '300px', marginTop: '8px' }}>
              <div className="progress-track" style={{ height: '6px' }}>
                <div className="progress-fill" style={{
                  width: `${progress}%`,
                  background: 'var(--accent-primary)',
                  transition: 'width 0.5s ease',
                }} />
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px', textAlign: 'center' }}>
                {progress}% complete
              </p>
            </div>

            <div className="loading-steps">
              {LOADING_STEPS.map((step, i) => {
                const StepIcon = step.icon;
                const status = i < loadingStep ? 'done' : i === loadingStep ? 'active' : '';
                return (
                  <div key={i} className={`loading-step ${status}`}>
                    {status === 'done' ? (
                      <Check size={16} color="var(--risk-low)" />
                    ) : status === 'active' ? (
                      <div className="loading-spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                    ) : (
                      <StepIcon size={16} />
                    )}
                    {step.label}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Results */}
        {analysisResult && (
          <>
            {/* Stats Bar */}
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon total"><FileText size={22} /></div>
                <div>
                  <div className="stat-value">{analysisResult.total_pages}</div>
                  <div className="stat-label">Pages Analyzed</div>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon high"><AlertTriangle size={22} /></div>
                <div>
                  <div className="stat-value" style={{ color: 'var(--risk-high)' }}>{analysisResult.risk_summary.high_risk}</div>
                  <div className="stat-label">High Risk</div>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon medium"><AlertCircle size={22} /></div>
                <div>
                  <div className="stat-value" style={{ color: 'var(--risk-medium)' }}>{analysisResult.risk_summary.medium_risk}</div>
                  <div className="stat-label">Medium Risk</div>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon low"><CheckCircle size={22} /></div>
                <div>
                  <div className="stat-value" style={{ color: 'var(--risk-low)' }}>{analysisResult.risk_summary.low_risk}</div>
                  <div className="stat-label">Low Risk</div>
                </div>
              </div>
            </div>

            {/* Info Bar */}
            <div className="info-bar">
              <span className="info-item"><FileText size={14} /> {analysisResult.document_name}</span>
              <span className="info-item"><Clock size={14} /> {analysisResult.processing_time}s</span>
              {modelHealth && (
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  {Object.entries(MODEL_LABELS).map(([key, meta]) => {
                    const active = modelHealth[key];
                    return (
                      <span key={key} className={`model-badge ${active ? 'active' : ''}`} style={{ '--badge-color': meta.color }}>
                        {active ? '●' : '○'} {meta.name}
                      </span>
                    );
                  })}
                </div>
              )}
              <button className="btn btn-ghost" style={{ marginLeft: 'auto', fontSize: '13px', padding: '6px 14px' }} onClick={clearAnalysis}>
                <Trash2 size={14} /> Clear & Upload New
              </button>
            </div>

            {/* Dashboard Grid */}
            <div className="dashboard-grid">
              <RiskOverview summary={analysisResult.risk_summary} />
              <div className="card">
                <div className="card-header">
                  <h3>🎯 Risk Distribution</h3>
                  {graphStats && (
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {graphStats.nodes} nodes · {graphStats.edges} edges
                    </span>
                  )}
                </div>
                <div className="card-body">
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    {[
                      { label: 'High Risk', value: analysisResult.risk_summary.risk_distribution?.HIGH || 0, color: '#ef4444' },
                      { label: 'Medium Risk', value: analysisResult.risk_summary.risk_distribution?.MEDIUM || 0, color: '#f59e0b' },
                      { label: 'Low Risk', value: analysisResult.risk_summary.risk_distribution?.LOW || 0, color: '#10b981' },
                    ].map(item => (
                      <div key={item.label}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '13px' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
                          <span style={{ fontWeight: 600, color: item.color }}>{item.value}%</span>
                        </div>
                        <div className="progress-track">
                          <div className="progress-fill" style={{ width: `${item.value}%`, background: item.color }} />
                        </div>
                      </div>
                    ))}
                  </div>
                  {graphStats && graphStats.edges > 0 && (
                    <div className="graph-stats-box">
                      <p className="graph-stats-title">
                        <Network size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} /> Clause Graph
                      </p>
                      <div className="graph-stats-grid">
                        <div><div className="gs-value">{graphStats.nodes}</div><div className="gs-label">Nodes</div></div>
                        <div><div className="gs-value">{graphStats.edges}</div><div className="gs-label">Edges</div></div>
                        <div><div className="gs-value">{(graphStats.max_centrality * 100).toFixed(1)}%</div><div className="gs-label">Max Centrality</div></div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Novelty Banner */}
            {novelty && (
              <div className="novelty-banner">
                <div className="novelty-header"><Info size={16} /> Why This System Is Different From ChatGPT</div>
                <div className="novelty-tags">
                  {novelty.structured_classification && <span className="novelty-tag">✓ Structured Classification</span>}
                  {novelty.calibrated_confidence && <span className="novelty-tag">✓ Calibrated Confidence</span>}
                  {novelty.graph_based_prioritization && <span className="novelty-tag">✓ Graph-Based Prioritization</span>}
                  {novelty.deterministic_output && <span className="novelty-tag">✓ Deterministic Output</span>}
                  {novelty.dual_model_fallback && <span className="novelty-tag">✓ Dual-Model Fallback</span>}
                </div>
                <p className="novelty-desc">{novelty.description}</p>
              </div>
            )}

            {/* Top Risky Clauses */}
            {topRiskyClauses.length > 0 && (
              <div className="card" style={{ marginBottom: '24px' }}>
                <div className="card-header">
                  <h3>🔥 Top Risky Clauses</h3>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Sorted by risk score</span>
                </div>
                <div className="card-body" style={{ padding: '12px 24px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {topRiskyClauses.map((clause, idx) => {
                      const riskColor = clause.risk_level === 'HIGH' ? '#ef4444' : clause.risk_level === 'MEDIUM' ? '#f59e0b' : '#10b981';
                      return (
                        <div key={clause.id} className="top-risky-item"
                          style={{ borderLeftColor: riskColor, background: idx === 0 ? 'var(--risk-high-bg)' : undefined }}
                          onClick={() => {
                            const full = analysisResult.clauses.find(c => c.id === clause.id);
                            if (full) setSelectedClause(full);
                          }}
                        >
                          <span className="top-risky-rank">#{idx + 1}</span>
                          <span className="top-risky-type">{clause.clause_type}</span>
                          <span className={`risk-badge ${clause.risk_level.toLowerCase()}`} style={{ fontSize: '10px', padding: '2px 8px' }}>
                            {clause.risk_level}
                          </span>
                          <span className="top-risky-score" style={{ color: riskColor }}>
                            {(clause.risk_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            <ClauseList clauses={analysisResult.clauses} onSelectClause={setSelectedClause} />
          </>
        )}
      </div>

      {selectedClause && (
        <ClauseDetail clause={selectedClause} onClose={() => setSelectedClause(null)} />
      )}
    </>
  );
}
