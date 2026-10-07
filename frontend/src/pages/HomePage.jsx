import { useNavigate } from 'react-router-dom';
import { Shield, Scan, Brain, Scale, ArrowRight, Sparkles } from 'lucide-react';

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page">
      <div className="landing-hero">
        <div className="landing-badge">
          <Sparkles size={14} />
          CCRAG-Powered Legal Intelligence
        </div>

        <h1>
          Decode Your Contracts.<br />
          <span className="gradient-text">Guard Your Future.</span>
        </h1>

        <p className="subtitle">
          AI-powered contract risk analysis that identifies, classifies, and explains 
          dangerous clauses — backed by Legal-BERT, confidence calibration, and real case law.
        </p>

        <div className="landing-cta">
          <button className="btn btn-primary btn-lg" onClick={() => navigate('/analyze')}>
            Start Analyzing
            <ArrowRight size={18} />
          </button>
          <button className="btn btn-secondary btn-lg" onClick={() => navigate('/cases')}>
            Explore Case Studies
          </button>
        </div>

        <div className="landing-features">
          <div className="feature-card">
            <div className="feature-icon">
              <Scan size={22} color="white" />
            </div>
            <h3>Clause Detection</h3>
            <p>Automatically segments contracts into individual clauses and classifies 41+ clause types with confidence scores.</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <Brain size={22} color="white" />
            </div>
            <h3>Risk Intelligence</h3>
            <p>Proprietary risk taxonomy maps each clause to HIGH, MEDIUM, or LOW risk with calibrated confidence levels.</p>
          </div>

          <div className="feature-card">
            <div className="feature-icon">
              <Scale size={22} color="white" />
            </div>
            <h3>Case Law Matching</h3>
            <p>Links risky clauses to real legal cases — see how similar clauses affected real companies and people.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
