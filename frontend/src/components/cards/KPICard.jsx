export default function KPICard({ label, value, sublabel, color = 'teal', delta }) {
  const colorMap = {
    teal: 'border-brand-teal text-brand-teal',
    orange: 'border-brand-orange text-brand-orange',
    red: 'border-red-500 text-red-500',
    yellow: 'border-yellow-500 text-yellow-500',
  };

  const fmt = typeof value === 'number'
    ? value.toLocaleString()
    : value || '--';

  return (
    <div className={`bg-gray-900 border-l-4 ${colorMap[color] || colorMap.teal} rounded-lg p-4`}>
      <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">{label}</div>
      <div className="flex items-baseline gap-2">
        <div className="text-2xl font-bold text-white">{fmt}</div>
        {delta != null && delta !== 0 && (
          <span className={`text-xs font-medium ${delta > 0 ? 'text-red-400' : 'text-green-400'}`}>
            {delta > 0 ? '+' : ''}{typeof delta === 'number' && Math.abs(delta) > 999
              ? `${(delta / 1000).toFixed(0)}K`
              : delta.toLocaleString()}
          </span>
        )}
      </div>
      {sublabel && <div className="text-xs text-gray-500 mt-1">{sublabel}</div>}
    </div>
  );
}
