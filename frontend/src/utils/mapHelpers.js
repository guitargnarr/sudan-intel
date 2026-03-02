/**
 * Shared map helper functions used by both SudanMap (Leaflet)
 * and SudanMapGL (deck.gl) components.
 */

export const SEVERITY_COLORS = [
  { threshold: 80, color: '#7f1d1d', rgb: [127, 29, 29] },
  { threshold: 60, color: '#ef4444', rgb: [239, 68, 68] },
  { threshold: 40, color: '#f97316', rgb: [249, 115, 22] },
  { threshold: 20, color: '#f59e0b', rgb: [245, 158, 11] },
  { threshold: 0,  color: '#14b8a6', rgb: [20, 184, 166] },
];

export function getColor(severity) {
  for (const { threshold, color } of SEVERITY_COLORS) {
    if (severity >= threshold) return color;
  }
  return '#14b8a6';
}

export function getColorRgba(severity, alpha = 180) {
  for (const { threshold, rgb } of SEVERITY_COLORS) {
    if (severity >= threshold) return [...rgb, alpha];
  }
  return [20, 184, 166, alpha];
}

export function buildRegionLookup(regions) {
  const lookup = {};
  if (!regions) return lookup;
  for (const r of regions) {
    lookup[r.code] = r;
    lookup[r.name] = r;
    lookup[r.name?.replace(/\s+/g, '')] = r;
    lookup[r.name?.toLowerCase()] = r;
  }
  return lookup;
}

export function findRegion(feature, regionLookup) {
  const p = feature.properties || {};
  const name1 = p.NAME_1 || '';
  const adminName = p.admin1Name || p.ADM1_EN || p.shapeName || '';
  const adminCode = p.admin1Pcode || p.ADM1_PCODE || '';

  return regionLookup[adminCode] || regionLookup[name1]
    || regionLookup[name1.toLowerCase()] || regionLookup[adminName]
    || regionLookup[adminName.replace(/\s+/g, '')] || null;
}

export function getDisplayName(feature) {
  const p = feature.properties || {};
  return p.NAME_1 || p.admin1Name || p.ADM1_EN || p.shapeName || 'Unknown';
}

export function getRegionCode(feature) {
  const p = feature.properties || {};
  return p.admin1Pcode || p.ADM1_PCODE || p.GID_1 || '';
}
