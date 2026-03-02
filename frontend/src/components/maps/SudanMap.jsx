import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import { useNavigate } from 'react-router-dom';

const SEVERITY_COLORS = [
  { threshold: 80, color: '#7f1d1d' },
  { threshold: 60, color: '#ef4444' },
  { threshold: 40, color: '#f97316' },
  { threshold: 20, color: '#f59e0b' },
  { threshold: 0, color: '#14b8a6' },
];

function getColor(severity) {
  for (const { threshold, color } of SEVERITY_COLORS) {
    if (severity >= threshold) return color;
  }
  return '#14b8a6';
}

export default function SudanMap({ regions }) {
  const [geoData, setGeoData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetch('/sudan-admin1.geojson')
      .then((r) => r.json())
      .then(setGeoData)
      .catch(() => setGeoData(null));
  }, []);

  // Build lookup that matches both API region names and GADM NAME_1
  const regionLookup = {};
  if (regions) {
    for (const r of regions) {
      regionLookup[r.code] = r;
      regionLookup[r.name] = r;
      // Also index by normalized name (no spaces) for GADM matching
      regionLookup[r.name?.replace(/\s+/g, '')] = r;
      regionLookup[r.name?.toLowerCase()] = r;
    }
  }

  function findRegion(feature) {
    const p = feature.properties || {};
    // Try GADM properties
    const name1 = p.NAME_1 || '';
    const gid = p.GID_1 || '';
    // Try HDX/OCHA properties
    const adminName = p.admin1Name || p.ADM1_EN || p.shapeName || '';
    const adminCode = p.admin1Pcode || p.ADM1_PCODE || '';

    return regionLookup[adminCode] || regionLookup[name1]
      || regionLookup[name1.toLowerCase()] || regionLookup[adminName]
      || regionLookup[adminName.replace(/\s+/g, '')] || null;
  }

  function getDisplayName(feature) {
    const p = feature.properties || {};
    return p.NAME_1 || p.admin1Name || p.ADM1_EN || p.shapeName || 'Unknown';
  }

  function getRegionCode(feature) {
    const p = feature.properties || {};
    return p.admin1Pcode || p.ADM1_PCODE || p.GID_1 || '';
  }

  const style = (feature) => {
    const region = findRegion(feature);
    const severity = region?.severity || 0;

    return {
      fillColor: getColor(severity),
      weight: 1,
      color: '#4b5563',
      fillOpacity: 0.7,
    };
  };

  const onEachFeature = (feature, layer) => {
    const name = getDisplayName(feature);
    const code = getRegionCode(feature);
    const region = findRegion(feature);

    const fat = region?.fatalities || 0;
    const fatLine = fat > 0
      ? `Fatalities: ${fat.toLocaleString()}`
      : 'Fatalities: No recorded events';
    layer.bindTooltip(
      `<strong>${name}</strong><br/>` +
      `Severity: ${region?.severity || 0}/100<br/>` +
      `IDPs: ${(region?.idps || 0).toLocaleString()}<br/>` +
      fatLine,
      { sticky: true }
    );

    layer.on('click', () => {
      if (code) navigate(`/region/${code}`);
    });
  };

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Crisis Severity by State</h3>
      <div className="rounded-lg overflow-hidden" style={{ height: 400 }}>
        <MapContainer
          center={[15.5, 30.0]}
          zoom={5}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={false}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; CartoDB'
          />
          {geoData && (
            <GeoJSON
              data={geoData}
              style={style}
              onEachFeature={onEachFeature}
            />
          )}
        </MapContainer>
      </div>
      <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: '#14b8a6' }} /> Low
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: '#f59e0b' }} /> Moderate
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: '#f97316' }} /> High
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: '#ef4444' }} /> Critical
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: '#7f1d1d' }} /> Catastrophic
        </span>
      </div>
    </div>
  );
}
