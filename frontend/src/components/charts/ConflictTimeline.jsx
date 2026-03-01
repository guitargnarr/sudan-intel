import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

export default function ConflictTimeline({ data }) {
  if (!data || data.length === 0) {
    return <div className="text-gray-500 text-sm p-4">No conflict timeline data available</div>;
  }

  // Aggregate by date
  const byDate = {};
  for (const d of data) {
    if (!d.date) continue;
    const key = d.date.slice(0, 7); // YYYY-MM
    if (!byDate[key]) byDate[key] = { date: key, events: 0, fatalities: 0 };
    byDate[key].events += d.events || 0;
    byDate[key].fatalities += d.fatalities || 0;
  }

  const chartData = Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date));

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Conflict Timeline</h3>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} />
          <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
            labelStyle={{ color: '#d1d5db' }}
          />
          <Area
            type="monotone"
            dataKey="events"
            stroke="#14b8a6"
            fill="#14b8a6"
            fillOpacity={0.2}
            name="Events"
          />
          <Area
            type="monotone"
            dataKey="fatalities"
            stroke="#ef4444"
            fill="#ef4444"
            fillOpacity={0.15}
            name="Fatalities"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
