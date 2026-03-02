import { Link, useLocation } from 'react-router-dom';
import { Activity } from 'lucide-react';

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gray-950">
      {/* Film grain overlay */}
      <div className="noise-overlay" />

      <header className="border-b border-white/[0.06] bg-gray-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <Activity className="w-5 h-5 text-brand-teal group-hover:text-brand-teal/80 transition-colors" />
            <span className="text-lg font-semibold tracking-tight text-white">
              Sudan<span className="text-brand-teal">Intel</span>
            </span>
          </Link>
          <div className="text-[11px] tracking-[0.1em] uppercase text-gray-600 hidden sm:block">
            Humanitarian Intelligence
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {children}
      </main>

      <footer className="border-t border-white/[0.04] mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center">
          <div className="text-[11px] tracking-[0.05em] text-gray-700">
            Built for those who cannot wait
          </div>
        </div>
      </footer>
    </div>
  );
}
