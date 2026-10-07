import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const RISK_COLORS = {
  HIGH: '#ef4444',
  MEDIUM: '#f59e0b',
  LOW: '#10b981',
};

export default function RiskOverview({ summary }) {
  if (!summary) return null;

  const chartData = [
    { name: 'High Risk', value: summary.high_risk, color: RISK_COLORS.HIGH },
    { name: 'Medium Risk', value: summary.medium_risk, color: RISK_COLORS.MEDIUM },
    { name: 'Low Risk', value: summary.low_risk, color: RISK_COLORS.LOW },
  ].filter(d => d.value > 0);

  const riskLevel = summary.overall_risk_score >= 60 ? 'HIGH' : summary.overall_risk_score >= 30 ? 'MEDIUM' : 'LOW';
  const riskColor = RISK_COLORS[riskLevel];

  return (
    <div className="card">
      <div className="card-header">
        <h3>📊 Risk Overview</h3>
        <span className={`risk-badge ${riskLevel.toLowerCase()}`}>
          {riskLevel} RISK
        </span>
      </div>
      <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
        {/* Donut Chart */}
        <div style={{ width: 180, height: 180, position: 'relative' }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={80}
                paddingAngle={4}
                dataKey="value"
                strokeWidth={0}
              >
                {chartData.map((entry, index) => (
                  <Cell key={index} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: '#1a2035',
                  border: '1px solid rgba(99,102,241,0.2)',
                  borderRadius: '8px',
                  fontSize: '13px',
                  color: '#f1f5f9'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          {/* Center text */}
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '28px', fontWeight: 800, color: riskColor, letterSpacing: '-1px' }}>
              {Math.round(summary.overall_risk_score)}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Risk Score
            </div>
          </div>
        </div>

        {/* Stats */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: RISK_COLORS.HIGH }} />
            <span style={{ color: 'var(--text-secondary)', fontSize: '14px', flex: 1 }}>High Risk</span>
            <span style={{ fontWeight: 700, fontSize: '18px', color: RISK_COLORS.HIGH }}>{summary.high_risk}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: RISK_COLORS.MEDIUM }} />
            <span style={{ color: 'var(--text-secondary)', fontSize: '14px', flex: 1 }}>Medium Risk</span>
            <span style={{ fontWeight: 700, fontSize: '18px', color: RISK_COLORS.MEDIUM }}>{summary.medium_risk}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: RISK_COLORS.LOW }} />
            <span style={{ color: 'var(--text-secondary)', fontSize: '14px', flex: 1 }}>Low Risk</span>
            <span style={{ fontWeight: 700, fontSize: '18px', color: RISK_COLORS.LOW }}>{summary.low_risk}</span>
          </div>
          <div style={{ 
            marginTop: '8px', 
            padding: '12px', 
            background: 'var(--bg-primary)', 
            borderRadius: 'var(--radius-md)',
            fontSize: '13px',
            color: 'var(--text-secondary)'
          }}>
            <strong style={{ color: 'var(--text-primary)' }}>{summary.total_clauses}</strong> clauses analyzed
          </div>
        </div>
      </div>
    </div>
  );
}
