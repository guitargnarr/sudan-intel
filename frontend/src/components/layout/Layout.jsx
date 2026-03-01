import { Link, useLocation } from 'react-router-dom';
import { BarChart3, Map, AlertTriangle, Newspaper, Activity } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: BarChart3 },
];

export default function Layout({ children }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-950">
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <Activity className="w-6 h-6 text-brand-teal" />
            <h1 className="text-xl font-bold text-white">
              Sudan <span className="text-brand-teal">Intel</span>
            </h1>
          </Link>
          <div className="text-xs text-gray-500">
            Humanitarian Intelligence Platform
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6">
        {children}
      </main>
      <footer className="border-t border-gray-800 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center text-xs text-gray-600">
          Data: HDX HAPI / ACLED / UNHCR / GDELT | AI: Local Ollama | Built to fight for those who cannot fight for themselves
        </div>
      </footer>
    </div>
  );
}
