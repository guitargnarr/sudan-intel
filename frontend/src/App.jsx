import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import RegionDetail from './pages/RegionDetail';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/region/:code" element={<RegionDetail />} />
      </Routes>
    </Layout>
  );
}
