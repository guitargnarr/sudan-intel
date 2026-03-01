export default function KPICard({ label, value, sublabel, color = 'teal' }) {
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
      <div className="text-2xl font-bold text-white">{fmt}</div>
      {sublabel && <div className="text-xs text-gray-500 mt-1">{sublabel}</div>}
    </div>
  );
}
