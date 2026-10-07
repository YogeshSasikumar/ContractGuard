import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import HomePage from './pages/HomePage';
import AnalysisPage from './pages/AnalysisPage';
import CasesPage from './pages/CasesPage';
import HistoryPage from './pages/HistoryPage';
import ComparisonPage from './pages/ComparisonPage';
import './index.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route element={<Layout />}>
          <Route path="/analyze" element={<AnalysisPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/comparison" element={<ComparisonPage />} />
          <Route path="/cases" element={<CasesPage />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
