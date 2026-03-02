/**
 * Pre-computed centroids for Sudan admin1 regions.
 * Computed from GADM 4.1 GeoJSON polygon coordinate averaging.
 *
 * Each entry keyed by GID_1 (GADM identifier).
 * Includes dbName (from HDX HAPI), geoName (from GeoJSON NAME_1),
 * and admin1 pcode (SDxx format used in routing).
 */

const CENTROIDS = {
  'SDN.1_1':  { geoName: 'AlJazirah',      dbName: 'Aj Jazirah',     code: 'SD15', lon: 33.0603, lat: 14.3553 },
  'SDN.2_1':  { geoName: 'AlQadarif',      dbName: 'Gedaref',        code: 'SD12', lon: 35.2996, lat: 14.1073 },
  'SDN.3_1':  { geoName: 'BlueNile',       dbName: 'Blue Nile',      code: 'SD08', lon: 34.4321, lat: 10.8084 },
  'SDN.4_1':  { geoName: 'CentralDarfur',  dbName: 'Central Darfur', code: 'SD06', lon: 23.3578, lat: 12.3648 },
  'SDN.5_1':  { geoName: 'EastDarfur',     dbName: 'East Darfur',    code: 'SD05', lon: 26.0234, lat: 11.7673 },
  'SDN.6_1':  { geoName: 'Kassala',        dbName: 'Kassala',        code: 'SD11', lon: 35.9794, lat: 15.8672 },
  'SDN.7_1':  { geoName: 'Khartoum',       dbName: 'Khartoum',       code: 'SD01', lon: 33.0802, lat: 15.7656 },
  'SDN.8_1':  { geoName: 'NorthDarfur',    dbName: 'North Darfur',   code: 'SD02', lon: 24.6469, lat: 13.9245 },
  'SDN.9_1':  { geoName: 'NorthKurdufan',  dbName: 'North Kordofan', code: 'SD13', lon: 30.7709, lat: 13.4821 },
  'SDN.10_1': { geoName: 'Northern',       dbName: 'Northern',       code: 'SD17', lon: 30.2539, lat: 20.9390 },
  'SDN.11_1': { geoName: 'RedSea',         dbName: 'Red Sea',        code: 'SD10', lon: 37.3553, lat: 19.9101 },
  'SDN.12_1': { geoName: 'RiverNile',      dbName: 'River Nile',     code: 'SD16', lon: 33.5807, lat: 19.5297 },
  'SDN.13_1': { geoName: 'Sennar',         dbName: 'Sennar',         code: 'SD14', lon: 34.3831, lat: 13.0987 },
  'SDN.14_1': { geoName: 'SouthDarfur',    dbName: 'South Darfur',   code: 'SD03', lon: 24.2466, lat: 10.1451 },
  'SDN.15_1': { geoName: 'SouthKurdufan',  dbName: 'South Kordofan', code: 'SD07', lon: 30.5585, lat: 11.8558 },
  'SDN.16_1': { geoName: 'WestDarfur',     dbName: 'West Darfur',    code: 'SD04', lon: 22.4305, lat: 13.3875 },
  'SDN.17_1': { geoName: 'WestKurdufan',   dbName: 'West Kordofan',  code: 'SD18', lon: 28.3564, lat: 12.1012 },
  'SDN.18_1': { geoName: 'WhiteNile',      dbName: 'White Nile',     code: 'SD09', lon: 32.4962, lat: 13.9218 },
};

// Build reverse lookups
const BY_NAME = {};
const BY_CODE = {};

for (const [gid, entry] of Object.entries(CENTROIDS)) {
  const full = { ...entry, gid };
  BY_NAME[entry.dbName] = full;
  BY_NAME[entry.dbName.toLowerCase()] = full;
  BY_NAME[entry.dbName.replace(/\s+/g, '')] = full;
  BY_NAME[entry.geoName] = full;
  BY_NAME[entry.geoName.toLowerCase()] = full;
  BY_CODE[entry.code] = full;
}

export function getCentroid(identifier) {
  if (!identifier) return null;
  return BY_NAME[identifier]
    || BY_CODE[identifier]
    || BY_NAME[identifier.replace(/\s+/g, '')]
    || BY_NAME[identifier.toLowerCase()]
    || null;
}

export { CENTROIDS, BY_CODE };
