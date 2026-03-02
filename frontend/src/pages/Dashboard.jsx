import { useEffect, useState } from 'react';
import { api } from '../api/client';
import Hero from '../components/hero/Hero';
import KPICard from '../components/cards/KPICard';
import ConflictTimeline from '../components/charts/ConflictTimeline';
import SudanMap from '../components/maps/SudanMap';
import NewsFeed from '../components/news/NewsFeed';
import AIBriefing from '../components/synthesis/AIBriefing';
import {
  Loader2, CheckCircle, AlertCircle,
  ChevronDown, Info,
} from 'lucide-react';

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

const SOURCE_LABELS = {
  hdx_hapi: 'HDX HAPI',
  gdelt: 'GDELT',
  unhcr: 'UNHCR',
};

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [regions, setRegions] = useState(null);
  const [news, setNews] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showMethodology, setShowMethodology] = useState(false);
  const [loadPhase, setLoadPhase] = useState(0);

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

  // Progressive loading messages for cold-start awareness
  useEffect(() => {
    if (!loading) return;
    const t1 = setTimeout(() => setLoadPhase(1), 5000);
    const t2 = setTimeout(() => setLoadPhase(2), 15000);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [loading]);

  const loadMessages = [
    'Connecting to data sources...',
    'Backend is waking up -- free-tier cold start, usually 30-60s.',
    'Still connecting -- aggregating conflict, displacement, and food security data.',
  ];

  if (loading) {
    return (
      <>
        <Hero />
        <div className="flex flex-col items-center justify-center py-24">
          <Loader2 className="w-6 h-6 text-brand-teal animate-spin" />
          <span className="mt-3 text-sm text-gray-600 text-center max-w-md transition-opacity duration-500">
            {loadMessages[loadPhase]}
          </span>
        </div>
      </>
    );
  }

  if (error) {
    return (
      <>
        <Hero />
        <div className="flex flex-col items-center justify-center py-24">
          <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center mb-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
          </div>
          <div className="text-sm text-gray-400">
            Unable to reach data backend
          </div>
          <div className="text-[10px] text-gray-600 mt-1">
            Render free tier may need a moment to spin up.
          </div>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 text-xs tracking-wide uppercase text-brand-teal border border-brand-teal/20 rounded-lg hover:bg-brand-teal/10 transition-colors"
          >
            Retry
          </button>
        </div>
      </>
    );
  }

  const kpis = dashboard?.kpis || {};
  const freshness = (dashboard?.data_freshness || [])
    .filter(s => s.source !== 'reliefweb');
  const healthyCount = freshness.filter(s => s.is_healthy).length;

  return (
    <div className="space-y-8">
      <Hero />

      {/* Inline source status -- minimal */}
      <div className="flex items-center justify-between flex-wrap gap-3 px-1">
        <div className="flex items-center gap-4">
          {freshness.map((s) => (
            <div key={s.source} className="flex items-center gap-1.5 text-xs">
              {s.is_healthy ? (
                <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
              ) : (
                <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
              )}
              <span className="text-gray-500">
                {SOURCE_LABELS[s.source] || s.source}
              </span>
              <span className={`${freshnessColor(s.last_success)}`}>
                {timeAgo(s.last_success)}
              </span>
            </div>
          ))}
        </div>
        <div className="text-[10px] text-gray-700 tracking-wide">
          {healthyCount}/{freshness.length} sources active
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          label="Internally Displaced"
          value={kpis.total_idps}
          delta={kpis.idp_change}
          sublabel={kpis.idp_period
            ? `${kpis.idp_source || 'IOM DTM'} \u2014 ${new Date(kpis.idp_period).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}`
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

      {/* Food Prices + Refugees Abroad */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {dashboard?.food_prices?.length > 0 && (
          <div className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-5">
            <h3 className="text-xs font-medium tracking-wide uppercase text-gray-500 mb-4">
              Commodity Prices
            </h3>
            <div className="space-y-2.5">
              {dashboard.food_prices.map((p, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span className="text-gray-400 truncate mr-2">{p.commodity}</span>
                  <span className="text-white font-medium whitespace-nowrap">
                    {p.price.toLocaleString()} {p.currency}/{p.unit}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cross-border displacement */}
        <div className="bg-white/[0.02] border border-white/[0.06] rounded-lg p-5">
          <h3 className="text-xs font-medium tracking-wide uppercase text-gray-500 mb-4">
            Cross-Border Displacement
          </h3>
          <div className="space-y-4">
            <div>
              <div className="text-3xl font-semibold text-white tracking-tight">
                {(dashboard?.refugees_total?.total || 2466231).toLocaleString()}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Sudanese refugees abroad (UNHCR {dashboard?.refugees_total?.year || 2025})
              </div>
            </div>
            <div className="accent-line" />
            <div className="text-xs text-gray-500 leading-relaxed">
              Primary host countries: Chad, Egypt, South Sudan,
              Ethiopia, Central African Republic, Libya, Uganda.
              Per-country breakdowns updated annually by UNHCR.
            </div>
          </div>
        </div>
      </div>

      {/* AI Briefing */}
      <AIBriefing brief={dashboard?.latest_brief} />

      {/* Data Methodology */}
      <div className="bg-white/[0.02] border border-white/[0.06] rounded-lg">
        <button
          onClick={() => setShowMethodology(!showMethodology)}
          className="w-full px-5 py-3.5 flex items-center justify-between text-left"
        >
          <div className="flex items-center gap-2">
            <Info className="w-3.5 h-3.5 text-gray-600" />
            <span className="text-xs tracking-wide text-gray-500">
              Data Sources & Methodology
            </span>
          </div>
          <ChevronDown className={`w-3.5 h-3.5 text-gray-600 transition-transform duration-300 ${showMethodology ? 'rotate-180' : ''}`} />
        </button>
        {showMethodology && (
          <div className="px-5 pb-5 text-xs text-gray-500 space-y-4 border-t border-white/[0.04] pt-4">
            <MethodNote
              title="IDP figures (IOM DTM via HDX HAPI)"
              body="Stock figures representing total displaced population at a point in time. Sub-national data aggregated from admin2-level assessments."
            />
            <MethodNote
              title="Conflict data (ACLED via HDX HAPI)"
              body="Coded conflict events and fatalities with 1-2 week reporting lag. Events in areas with limited access may be undercounted."
            />
            <MethodNote
              title="Food security (IPC via HDX HAPI)"
              body="Most recent IPC phase classifications. Areas with access constraints cannot be assessed -- Phase 4-5 figures are likely undercounts."
            />
            <MethodNote
              title="Displacement (UNHCR)"
              body="National-level annual snapshots of registered refugee and IDP populations. Does not capture unregistered displacement."
            />
            <MethodNote
              title="News monitoring (GDELT)"
              body="Filtered for Sudan relevance with domain and keyword verification. Automated media monitoring, not verified reporting."
            />
          </div>
        )}
      </div>
    </div>
  );
}

function MethodNote({ title, body }) {
  return (
    <div>
      <span className="text-gray-400 font-medium">{title}</span>
      <p className="mt-0.5 leading-relaxed">{body}</p>
    </div>
  );
}
