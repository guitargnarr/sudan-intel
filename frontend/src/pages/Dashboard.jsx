import { useEffect, useState } from 'react';
import { api } from '../api/client';
import KPICard from '../components/cards/KPICard';
import ConflictTimeline from '../components/charts/ConflictTimeline';
import SudanMap from '../components/maps/SudanMap';
import NewsFeed from '../components/news/NewsFeed';
import AIBriefing from '../components/synthesis/AIBriefing';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [regions, setRegions] = useState(null);
  const [news, setNews] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [d, r, n] = await Promise.all([
          api.dashboard(),
          api.regions(),
          api.news(15),
        ]);
        setDashboard(d);
        setRegions(r);
        setNews(n);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-brand-teal animate-spin" />
        <span className="ml-3 text-gray-400">Loading humanitarian data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded-lg p-6 text-center">
        <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <div className="text-red-300">{error}</div>
        <div className="text-xs text-gray-500 mt-2">
          Ensure the backend is running on port 8900
        </div>
      </div>
    );
  }

  const kpis = dashboard?.kpis || {};

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          label="Internally Displaced"
          value={kpis.total_idps}
          color="orange"
        />
        <KPICard
          label="Conflict Events"
          value={kpis.total_conflict_events}
          color="red"
        />
        <KPICard
          label="Fatalities"
          value={kpis.total_fatalities}
          color="red"
        />
        <KPICard
          label="IPC 4-5 Population"
          value={kpis.ipc_emergency_population}
          sublabel="Emergency + Famine"
          color="orange"
        />
      </div>

      {/* Map + News */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SudanMap regions={regions} />
        </div>
        <div>
          <NewsFeed articles={news?.articles} />
        </div>
      </div>

      {/* Conflict Timeline */}
      <ConflictTimeline data={dashboard?.conflict_timeline} />

      {/* AI Briefing */}
      <AIBriefing brief={dashboard?.latest_brief} />

      {/* Data Freshness */}
      {dashboard?.data_freshness?.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Data Sources</h3>
          <div className="flex flex-wrap gap-3">
            {dashboard.data_freshness.map((s) => (
              <div
                key={s.source}
                className="flex items-center gap-1.5 text-xs"
              >
                {s.is_healthy ? (
                  <CheckCircle className="w-3 h-3 text-green-500" />
                ) : (
                  <AlertCircle className="w-3 h-3 text-red-500" />
                )}
                <span className="text-gray-400">{s.source}</span>
                <span className="text-gray-600">
                  {s.last_success
                    ? new Date(s.last_success).toLocaleTimeString()
                    : 'never'}
                </span>
                <span className="text-gray-600">({s.records?.toLocaleString()} records)</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
