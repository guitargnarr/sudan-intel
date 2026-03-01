import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import KPICard from '../components/cards/KPICard';
import ConflictTimeline from '../components/charts/ConflictTimeline';
import AIBriefing from '../components/synthesis/AIBriefing';
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react';

export default function RegionDetail() {
  const { code } = useParams();
  const [region, setRegion] = useState(null);
  const [synthesis, setSynthesis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function load() {
      try {
        const [r, s] = await Promise.all([
          api.region(code),
          api.synthesis('admin1', code),
        ]);
        setRegion(r);
        setSynthesis(s);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [code]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-brand-teal animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded-lg p-6 text-center">
        <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <div className="text-red-300">{error}</div>
      </div>
    );
  }

  const conflicts = region?.conflict || [];
  const displacements = region?.displacement || [];
  const foodSecurity = region?.food_security || [];
  const orgs = region?.operational_presence || [];

  const totalEvents = conflicts.reduce((s, c) => s + (c.events || 0), 0);
  const totalFatalities = conflicts.reduce((s, c) => s + (c.fatalities || 0), 0);
  const totalIDPs = displacements.reduce((s, d) => s + (d.population || 0), 0);
  const regionName = region?.admin1_name || conflicts[0]?.admin1 || displacements[0]?.admin1 || code;

  // IPC distribution
  const ipcDist = {};
  for (const f of foodSecurity) {
    const p = f.phase || 'unknown';
    ipcDist[p] = (ipcDist[p] || 0) + (f.population || 0);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/" className="text-gray-400 hover:text-brand-teal transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h2 className="text-xl font-bold text-white">{regionName}</h2>
        <span className="text-xs text-gray-500">{code}</span>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard label="Conflict Events" value={totalEvents} color="red" />
        <KPICard label="Fatalities" value={totalFatalities} color="red" />
        <KPICard label="Displaced" value={totalIDPs} color="orange" />
        <KPICard label="Organizations" value={new Set(orgs.map(o => o.acronym)).size} color="teal" />
      </div>

      {/* Conflict Timeline */}
      <ConflictTimeline
        data={conflicts.map(c => ({
          date: c.date,
          events: c.events,
          fatalities: c.fatalities,
        }))}
      />

      {/* IPC Distribution */}
      {Object.keys(ipcDist).length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Food Security (IPC Phases)</h3>
          <div className="grid grid-cols-5 gap-2">
            {['1', '2', '3', '4', '5'].map((phase) => {
              const pop = ipcDist[phase] || 0;
              const labels = { 1: 'Minimal', 2: 'Stressed', 3: 'Crisis', 4: 'Emergency', 5: 'Famine' };
              const colors = { 1: 'bg-ipc-1 text-gray-900', 2: 'bg-ipc-2 text-gray-900', 3: 'bg-ipc-3 text-white', 4: 'bg-ipc-4 text-white', 5: 'bg-ipc-5 text-white' };
              return (
                <div key={phase} className={`${colors[phase]} rounded p-2 text-center`}>
                  <div className="text-xs font-bold">Phase {phase}</div>
                  <div className="text-sm font-semibold">{pop.toLocaleString()}</div>
                  <div className="text-xs opacity-80">{labels[phase]}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Operational Presence */}
      {orgs.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">
            Operational Presence ({new Set(orgs.map(o => o.acronym)).size} organizations)
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2 pr-4">Org</th>
                  <th className="text-left py-2 pr-4">Type</th>
                  <th className="text-left py-2 pr-4">Sector</th>
                  <th className="text-left py-2">Location</th>
                </tr>
              </thead>
              <tbody>
                {orgs.slice(0, 30).map((o, i) => (
                  <tr key={i} className="border-b border-gray-800/50">
                    <td className="py-1.5 pr-4 text-white font-medium">{o.acronym}</td>
                    <td className="py-1.5 pr-4 text-gray-400">{o.type}</td>
                    <td className="py-1.5 pr-4 text-gray-400">{o.sector}</td>
                    <td className="py-1.5 text-gray-500">{o.admin2}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* AI Brief */}
      <AIBriefing brief={synthesis} />
    </div>
  );
}
