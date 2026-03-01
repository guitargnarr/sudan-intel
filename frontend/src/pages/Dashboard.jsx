import { useEffect, useState } from 'react';
import { api } from '../api/client';
import KPICard from '../components/cards/KPICard';
import ConflictTimeline from '../components/charts/ConflictTimeline';
import SudanMap from '../components/maps/SudanMap';
import NewsFeed from '../components/news/NewsFeed';
import AIBriefing from '../components/synthesis/AIBriefing';
import { Loader2, CheckCircle, AlertCircle, Clock, RefreshCw } from 'lucide-react';

const SOURCE_LABELS = {
  hdx_hapi: 'HDX HAPI',
  gdelt: 'GDELT News',
  unhcr: 'UNHCR',
};

function timeAgo(iso) {
  if (!iso) return 'never';
  const diff = Date.now() - new Date(iso + 'Z').getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function freshnessColor(iso) {
  if (!iso) return 'text-red-400';
  const hrs = (Date.now() - new Date(iso + 'Z').getTime()) / 3600000;
  if (hrs < 1) return 'text-green-400';
  if (hrs < 12) return 'text-brand-teal';
  if (hrs < 24) return 'text-yellow-400';
  return 'text-red-400';
}

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [regions, setRegions] = useState(null);
  const [news, setNews] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fetchedAt, setFetchedAt] = useState(null);

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
        setFetchedAt(d.server_time || new Date().toISOString());
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

  const freshness = dashboard?.data_freshness || [];
  const allHealthy = freshness.length > 0 && freshness.every(s => s.is_healthy);
  const totalRecords = freshness.reduce((sum, s) => sum + (s.records || 0), 0);

  return (
    <div className="space-y-6">
      {/* Data Verification Bar */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg px-4 py-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            {allHealthy ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <AlertCircle className="w-4 h-4 text-yellow-500" />
            )}
            <span className="text-sm font-medium text-gray-300">
              {allHealthy ? 'All sources verified' : 'Source issues detected'}
            </span>
            <span className="text-xs text-gray-600 hidden sm:inline">
              {totalRecords.toLocaleString()} total records
            </span>
          </div>
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Clock className="w-3 h-3" />
            <span>
              Page loaded {fetchedAt
                ? new Date(fetchedAt.endsWith('Z') ? fetchedAt : fetchedAt + 'Z').toLocaleString('en-US', {
                    month: 'short', day: 'numeric',
                    hour: '2-digit', minute: '2-digit', hour12: true,
                  })
                : '--'}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 pt-3 border-t border-gray-800">
          {freshness.map((s) => (
            <div key={s.source} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5">
                {s.is_healthy ? (
                  <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-3 h-3 text-red-500 flex-shrink-0" />
                )}
                <span className="text-gray-300 font-medium">
                  {SOURCE_LABELS[s.source] || s.source}
                </span>
              </div>
              <div className="flex items-center gap-2 text-right">
                <span className="text-gray-500">
                  {(s.records || 0).toLocaleString()} rows
                </span>
                <span className={freshnessColor(s.last_success)}>
                  {timeAgo(s.last_success)}
                </span>
              </div>
            </div>
          ))}
        </div>
        {freshness.some(s => !s.is_healthy) && (
          <div className="mt-2 pt-2 border-t border-gray-800">
            {freshness.filter(s => !s.is_healthy).map(s => (
              <div key={s.source + '-err'} className="text-xs text-red-400">
                {SOURCE_LABELS[s.source] || s.source}: {s.last_error || 'Unhealthy'}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          label="Internally Displaced"
          value={kpis.total_idps}
          sublabel={kpis.idp_period
            ? `${kpis.idp_source || 'IOM DTM'} - ${new Date(kpis.idp_period).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}`
            : kpis.idp_source || 'Latest figure'}
          color="orange"
        />
        <KPICard
          label="Conflict Events"
          value={kpis.total_conflict_events}
          sublabel={kpis.conflict_window?.label || 'All time'}
          color="red"
        />
        <KPICard
          label="Fatalities"
          value={kpis.total_fatalities}
          sublabel={kpis.conflict_window?.label || 'All time'}
          color="red"
        />
        <KPICard
          label="IPC 4-5 Population"
          value={kpis.ipc_emergency_population}
          sublabel={kpis.ipc_period
            ? `As of ${new Date(kpis.ipc_period).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}`
            : 'Emergency + Famine'}
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

    </div>
  );
}
