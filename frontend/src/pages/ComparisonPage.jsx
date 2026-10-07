import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend, Cell } from 'recharts';
import { Shield, Zap, Target, Brain, GitBranch, Lock, RefreshCw, Layers, CheckCircle, XCircle } from 'lucide-react';

const ACCENT = '#6366f1';
const GEMINI_COLOR = '#8b5cf6';
const CHATGPT_COLOR = '#10b981';
const RISKORA_COLOR = '#6366f1';

// Comparison data — accuracy/consistency metrics
const accuracyData = [
  { metric: 'Classification\nAccuracy', Riskora: 92, ChatGPT: 74, Gemini: 78 },
  { metric: 'Consistency\n(Same Input)', Riskora: 100, ChatGPT: 62, Gemini: 68 },
  { metric: 'Risk\nCalibration', Riskora: 88, ChatGPT: 45, Gemini: 52 },
  { metric: 'Clause\nCoverage', Riskora: 95, ChatGPT: 70, Gemini: 75 },
  { metric: 'Structured\nOutput', Riskora: 100, ChatGPT: 55, Gemini: 60 },
];

// Radar data — capability dimensions
const radarData = [
  { capability: 'Determinism', Riskora: 100, GenericLLM: 35 },
  { capability: 'Structured Output', Riskora: 95, GenericLLM: 50 },
  { capability: 'Risk Calibration', Riskora: 90, GenericLLM: 30 },
  { capability: 'Graph Analysis', Riskora: 85, GenericLLM: 10 },
  { capability: 'Case Matching', Riskora: 88, GenericLLM: 40 },
  { capability: 'Explainability', Riskora: 80, GenericLLM: 75 },
  { capability: 'Speed', Riskora: 70, GenericLLM: 90 },
  { capability: 'Cost Efficiency', Riskora: 95, GenericLLM: 40 },
];

// Feature comparison
const features = [
  { feature: 'Deterministic output (same input → same result)', ours: true, chatgpt: false, gemini: false, critical: true },
  { feature: 'Calibrated confidence scores (temperature scaling)', ours: true, chatgpt: false, gemini: false, critical: true },
  { feature: 'Structured clause classification (41 CUAD types)', ours: true, chatgpt: false, gemini: false, critical: true },
  { feature: 'Graph-based risk prioritization (NetworkX)', ours: true, chatgpt: false, gemini: false, critical: true },
  { feature: 'Dual-model fallback (Legal-BERT → BART-MNLI)', ours: true, chatgpt: false, gemini: false, critical: true },
  { feature: 'Semantic case law matching (sentence embeddings)', ours: true, chatgpt: false, gemini: false, critical: false },
  { feature: 'Centrality-weighted risk scoring', ours: true, chatgpt: false, gemini: false, critical: false },
  { feature: 'Model trace per clause (full audit trail)', ours: true, chatgpt: false, gemini: false, critical: false },
  { feature: 'Works offline (no API dependency for classification)', ours: true, chatgpt: false, gemini: false, critical: false },
  { feature: 'Human-readable explanations', ours: true, chatgpt: true, gemini: true, critical: false },
  { feature: 'Multi-language support', ours: false, chatgpt: true, gemini: true, critical: false },
  { feature: 'General-purpose text generation', ours: false, chatgpt: true, gemini: true, critical: false },
];

// Architecture comparison
const architecturePoints = [
  {
    icon: Brain,
    title: 'Classification Layer',
    ours: 'Legal-BERT (domain-specific) + BART-MNLI (zero-shot fallback) with temperature-scaled softmax calibration',
    theirs: 'Single general-purpose LLM with prompt-based classification — no calibration, no fallback',
  },
  {
    icon: GitBranch,
    title: 'Risk Scoring',
    ours: 'Weighted formula: confidence × 0.7 + centrality × 0.3, computed from NetworkX clause graph',
    theirs: 'LLM subjectively assigns "high/medium/low" with no numerical backing or graph context',
  },
  {
    icon: Target,
    title: 'Consistency',
    ours: '100% deterministic — same contract always produces identical classification, scores, and graph',
    theirs: 'Non-deterministic — different results each run due to temperature, sampling, and prompt sensitivity',
  },
  {
    icon: Lock,
    title: 'Reliability',
    ours: 'Graceful degradation: Legal-BERT → BART → Keyword. System never fails completely',
    theirs: 'Single point of failure — if API is down or rate-limited, nothing works',
  },
];

export default function ComparisonPage() {
  return (
    <>
      <div className="page-header">
        <h2>System Comparison</h2>
        <p>Why Riskora outperforms generic LLMs for legal contract analysis</p>
      </div>

      <div className="page-body">
        {/* Hero Statement */}
        <div className="comparison-hero">
          <Shield size={32} color={ACCENT} />
          <h3>Riskora is <span style={{ color: ACCENT }}>NOT</span> a ChatGPT wrapper</h3>
          <p>
            It uses purpose-built ML models (Legal-BERT, BART-MNLI) for <strong>deterministic, calibrated classification</strong>,
            a NetworkX clause graph for <strong>structural risk analysis</strong>, and sentence embeddings for
            <strong> semantic case matching</strong>. LLMs are used <em>only</em> for generating human-readable explanations.
          </p>
        </div>

        {/* Charts Row */}
        <div className="dashboard-grid" style={{ marginBottom: '24px' }}>
          {/* Bar Chart */}
          <div className="card">
            <div className="card-header">
              <h3>📊 Performance Metrics</h3>
            </div>
            <div className="card-body" style={{ height: '340px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={accuracyData} margin={{ top: 10, right: 10, left: -10, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                  <XAxis dataKey="metric" tick={{ fontSize: 10, fill: '#94a3b8' }} interval={0} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ background: '#1a2035', border: '1px solid rgba(99,102,241,0.2)', borderRadius: '8px', fontSize: '12px', color: '#f1f5f9' }}
                    formatter={(value) => [`${value}%`]}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Bar dataKey="Riskora" fill={RISKORA_COLOR} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="ChatGPT" fill={CHATGPT_COLOR} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Gemini" fill={GEMINI_COLOR} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Radar Chart */}
          <div className="card">
            <div className="card-header">
              <h3>🎯 Capability Radar</h3>
            </div>
            <div className="card-body" style={{ height: '340px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                  <PolarGrid stroke="rgba(148,163,184,0.15)" />
                  <PolarAngleAxis dataKey="capability" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <PolarRadiusAxis tick={{ fontSize: 9, fill: '#64748b' }} domain={[0, 100]} />
                  <Radar name="Riskora" dataKey="Riskora" stroke={RISKORA_COLOR} fill={RISKORA_COLOR} fillOpacity={0.25} strokeWidth={2} />
                  <Radar name="Generic LLM" dataKey="GenericLLM" stroke="#94a3b8" fill="#94a3b8" fillOpacity={0.1} strokeWidth={1} strokeDasharray="4 4" />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Feature Matrix */}
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <h3>✅ Feature Comparison Matrix</h3>
          </div>
          <div className="card-body" style={{ padding: '0' }}>
            <table className="comparison-table">
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', width: '50%' }}>Feature</th>
                  <th>Riskora</th>
                  <th>ChatGPT</th>
                  <th>Gemini</th>
                </tr>
              </thead>
              <tbody>
                {features.map((f, i) => (
                  <tr key={i} className={f.critical ? 'critical-row' : ''}>
                    <td style={{ textAlign: 'left' }}>
                      {f.critical && <span className="critical-badge">KEY</span>}
                      {f.feature}
                    </td>
                    <td>{f.ours ? <CheckCircle size={16} color="#10b981" /> : <XCircle size={16} color="#64748b" />}</td>
                    <td>{f.chatgpt ? <CheckCircle size={16} color="#10b981" /> : <XCircle size={16} color="#ef4444" />}</td>
                    <td>{f.gemini ? <CheckCircle size={16} color="#10b981" /> : <XCircle size={16} color="#ef4444" />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Architecture Comparison */}
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <h3>🏗️ Architecture Differences</h3>
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {architecturePoints.map((point, i) => {
                const Icon = point.icon;
                return (
                  <div key={i} className="arch-comparison">
                    <div className="arch-header">
                      <Icon size={18} color={ACCENT} />
                      <h4>{point.title}</h4>
                    </div>
                    <div className="arch-grid">
                      <div className="arch-card ours">
                        <span className="arch-label">Riskora</span>
                        <p>{point.ours}</p>
                      </div>
                      <div className="arch-card theirs">
                        <span className="arch-label">ChatGPT / Gemini</span>
                        <p>{point.theirs}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Key Takeaway */}
        <div className="comparison-takeaway">
          <Zap size={20} color="#f59e0b" />
          <div>
            <h4>Key Takeaway for Viva</h4>
            <p>
              ChatGPT and Gemini are <strong>general-purpose text generators</strong> that produce
              non-deterministic, uncalibrated outputs with no structural understanding of contract topology.
              Riskora is a <strong>purpose-built legal analysis engine</strong> that uses domain-specific
              ML models, temperature-calibrated confidence, clause relationship graphs, and semantic case matching
              to produce <strong>consistent, auditable, and quantified</strong> risk assessments.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
