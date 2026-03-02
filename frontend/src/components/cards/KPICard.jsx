export default function KPICard({ label, value, sublabel, color = 'teal', delta }) {
  const accentMap = {
    teal: 'border-brand-teal/40 text-brand-teal',
    orange: 'border-brand-orange/40 text-brand-orange',
    red: 'border-red-500/40 text-red-500',
    yellow: 'border-yellow-500/40 text-yellow-500',
  };

  const fmt = typeof value === 'number'
    ? value.toLocaleString()
    : value || '--';

  return (
    <div className={`bg-white/[0.02] border border-white/[0.06] border-l-2 ${accentMap[color] || accentMap.teal} rounded-lg p-4`}>
      <div className="text-[10px] uppercase tracking-[0.1em] text-gray-500 mb-2">
        {label}
      </div>
      <div className="flex items-baseline gap-2">
        <div className="text-2xl font-semibold text-white tracking-tight">{fmt}</div>
        {delta != null && delta !== 0 && (
          <span className={`text-xs font-medium ${delta > 0 ? 'text-red-400' : 'text-green-400'}`}>
            {delta > 0 ? '+' : ''}{typeof delta === 'number' && Math.abs(delta) > 999
              ? `${(delta / 1000).toFixed(0)}K`
              : delta.toLocaleString()}
          </span>
        )}
      </div>
      {sublabel && (
        <div className="text-[10px] text-gray-600 mt-1.5">{sublabel}</div>
      )}
    </div>
  );
}
