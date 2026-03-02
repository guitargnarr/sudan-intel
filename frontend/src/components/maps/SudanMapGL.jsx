import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Map, useControl } from 'react-map-gl/maplibre';
import { MapboxOverlay } from '@deck.gl/mapbox';
import { ArcLayer, GeoJsonLayer, ScatterplotLayer } from '@deck.gl/layers';
import { getCentroid, getNeighborCentroid } from '../../constants/sudanCentroids';
import {
  getColorRgba, buildRegionLookup, findRegion, getDisplayName,
} from '../../utils/mapHelpers';

const DARK_BASEMAP =
  'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

const EVENT_TYPE_COLORS = {
  political_violence: [239, 68, 68],
  civilian_targeting: [249, 115, 22],
  demonstration:      [20, 184, 166],
};

const EVENT_TYPE_LABELS = {
  political_violence: 'Political Violence',
  civilian_targeting: 'Civilian Targeting',
  demonstration:      'Demonstrations',
};

const SUDAN_CENTER = [30.0, 15.5];

const INITIAL_VIEW = {
  longitude: 30.0,
  latitude: 15.5,
  zoom: 4.5,
  pitch: 0,
  bearing: 0,
};

function DeckGLOverlay(props) {
  const overlay = useControl(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}

export default function SudanMapGL({ regions, conflictTimeline, refugeesAbroad }) {
  const navigate = useNavigate();
  const [geoData, setGeoData] = useState(null);
  const [viewMode, setViewMode] = useState('all');
  const [activeTypes, setActiveTypes] = useState(
    new Set(Object.keys(EVENT_TYPE_LABELS))
  );
  const [periodIdx, setPeriodIdx] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const intervalRef = useRef(null);

  // Load GeoJSON
  useEffect(() => {
    fetch('/sudan-admin1.geojson')
      .then((r) => r.json())
      .then(setGeoData)
      .catch(() => setGeoData(null));
  }, []);

  // Sorted unique date periods
  const periods = useMemo(() => {
    if (!conflictTimeline) return [];
    const set = new Set(
      conflictTimeline.map((d) => d.date).filter(Boolean)
    );
    return [...set].sort();
  }, [conflictTimeline]);

  // Init slider to latest when periods arrive
  useEffect(() => {
    if (periods.length > 0 && periodIdx === -1) {
      setPeriodIdx(periods.length - 1);
    }
  }, [periods, periodIdx]);

  // Auto-play
  useEffect(() => {
    if (isPlaying && periods.length > 0) {
      intervalRef.current = setInterval(() => {
        setPeriodIdx((prev) => {
          if (prev >= periods.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 800);
    }
    return () => clearInterval(intervalRef.current);
  }, [isPlaying, periods.length]);

  const regionLookup = useMemo(
    () => buildRegionLookup(regions),
    [regions]
  );

  // Filter conflict data for current period + active types
  const scatterData = useMemo(() => {
    if (!conflictTimeline || periods.length === 0 || periodIdx < 0)
      return [];
    const currentDate = periods[periodIdx];
    if (!currentDate) return [];

    // Aggregate by region (sum across active event types)
    const byRegion = {};
    for (const d of conflictTimeline) {
      if (d.date !== currentDate) continue;
      if (!activeTypes.has(d.event_type)) continue;
      const centroid = getCentroid(d.region);
      if (!centroid) continue;

      const key = d.region;
      if (!byRegion[key]) {
        byRegion[key] = {
          position: [centroid.lon, centroid.lat],
          region: d.region,
          regionCode: d.region_code || centroid.code,
          events: 0,
          fatalities: 0,
          types: {},
        };
      }
      byRegion[key].events += d.events || 0;
      byRegion[key].fatalities += d.fatalities || 0;
      const t = d.event_type;
      byRegion[key].types[t] =
        (byRegion[key].types[t] || 0) + (d.events || 0);
    }
    return Object.values(byRegion);
  }, [conflictTimeline, periods, periodIdx, activeTypes]);

  // Compute max values for scaling
  const maxEvents = useMemo(
    () => Math.max(...scatterData.map((d) => d.events), 1),
    [scatterData]
  );
  const maxFatalities = useMemo(
    () => Math.max(...scatterData.map((d) => d.fatalities), 1),
    [scatterData]
  );

  // Displacement flow arc data
  const arcData = useMemo(() => {
    if (!refugeesAbroad) return [];
    return refugeesAbroad
      .filter((d) => d.refugees > 0)
      .map((d) => {
        const dest = getNeighborCentroid(d.country_code);
        if (!dest) return null;
        return {
          source: SUDAN_CENTER,
          target: [dest.lon, dest.lat],
          refugees: d.refugees,
          country: d.country,
          countryCode: d.country_code,
        };
      })
      .filter(Boolean);
  }, [refugeesAbroad]);

  const maxRefugees = useMemo(
    () => Math.max(...arcData.map((d) => d.refugees), 1),
    [arcData]
  );

  // deck.gl layers
  const layers = useMemo(() => {
    const result = [];

    // Choropleth layer
    if (geoData && (viewMode === 'severity' || viewMode === 'all')) {
      result.push(
        new GeoJsonLayer({
          id: 'choropleth',
          data: geoData,
          filled: true,
          stroked: true,
          getFillColor: (feature) => {
            const region = findRegion(feature, regionLookup);
            return getColorRgba(region?.severity || 0, 160);
          },
          getLineColor: [75, 85, 99, 200],
          getLineWidth: 1,
          lineWidthUnits: 'pixels',
          pickable: true,
          autoHighlight: true,
          highlightColor: [255, 255, 255, 40],
          onClick: (info) => {
            if (!info.object) return;
            const region = findRegion(info.object, regionLookup);
            if (region?.code) navigate(`/region/${region.code}`);
          },
          updateTriggers: {
            getFillColor: [regionLookup],
          },
        })
      );
    }

    // Conflict event scatterplot
    if (
      scatterData.length > 0 &&
      (viewMode === 'events' || viewMode === 'all')
    ) {
      result.push(
        new ScatterplotLayer({
          id: 'conflict-events',
          data: scatterData,
          getPosition: (d) => d.position,
          getRadius: (d) => {
            const t =
              Math.log(1 + d.events) / Math.log(1 + maxEvents);
            return 8000 + t * 42000;
          },
          getFillColor: (d) => {
            const t = d.fatalities / maxFatalities;
            return [
              Math.round(20 + t * 219),
              Math.round(184 - t * 116),
              Math.round(166 - t * 98),
              200,
            ];
          },
          radiusUnits: 'meters',
          pickable: true,
          transitions: {
            getRadius: { duration: 300 },
            getFillColor: { duration: 300 },
          },
          updateTriggers: {
            getRadius: [maxEvents],
            getFillColor: [maxFatalities],
          },
        })
      );
    }

    // Displacement flow arcs
    if (
      arcData.length > 0 &&
      (viewMode === 'flows' || viewMode === 'all')
    ) {
      result.push(
        new ArcLayer({
          id: 'displacement-flows',
          data: arcData,
          getSourcePosition: (d) => d.source,
          getTargetPosition: (d) => d.target,
          getSourceColor: [249, 115, 22, 200],
          getTargetColor: [20, 184, 166, 180],
          getWidth: (d) =>
            1 + (Math.log(1 + d.refugees) / Math.log(1 + maxRefugees)) * 6,
          widthUnits: 'pixels',
          getHeight: 0.3,
          pickable: true,
          transitions: {
            getWidth: { duration: 300 },
          },
          updateTriggers: {
            getWidth: [maxRefugees],
          },
        })
      );

      // Destination country dots
      result.push(
        new ScatterplotLayer({
          id: 'destination-dots',
          data: arcData,
          getPosition: (d) => d.target,
          getRadius: (d) => {
            const t =
              Math.log(1 + d.refugees) / Math.log(1 + maxRefugees);
            return 6000 + t * 30000;
          },
          getFillColor: [20, 184, 166, 140],
          radiusUnits: 'meters',
          pickable: true,
          updateTriggers: {
            getRadius: [maxRefugees],
          },
        })
      );
    }

    return result;
  }, [
    geoData, viewMode, regionLookup, scatterData,
    maxEvents, maxFatalities, navigate,
    arcData, maxRefugees,
  ]);

  // Tooltip handler
  const getTooltip = useCallback(
    ({ object, layer }) => {
      if (!object) return null;
      const style = {
        backgroundColor: '#1f2937',
        color: '#d1d5db',
        border: '1px solid #374151',
        borderRadius: '8px',
        padding: '8px 12px',
        fontSize: '12px',
        lineHeight: '1.5',
      };

      if (layer?.id === 'choropleth') {
        const name = getDisplayName(object);
        const region = findRegion(object, regionLookup);
        const fat = region?.fatalities || 0;
        const fatLine =
          fat > 0
            ? `Fatalities: ${fat.toLocaleString()}`
            : 'Fatalities: No recorded events';
        return {
          html:
            `<strong>${name}</strong><br/>` +
            `Severity: ${region?.severity || 0}/100<br/>` +
            `IDPs: ${(region?.idps || 0).toLocaleString()}<br/>` +
            fatLine,
          style,
        };
      }

      if (layer?.id === 'conflict-events') {
        const typeLines = Object.entries(object.types)
          .map(
            ([t, count]) =>
              `${EVENT_TYPE_LABELS[t] || t}: ${count}`
          )
          .join('<br/>');
        return {
          html:
            `<strong>${object.region}</strong><br/>` +
            `Events: ${object.events.toLocaleString()}<br/>` +
            `Fatalities: ${object.fatalities.toLocaleString()}` +
            (typeLines
              ? `<br/><span style="border-top:1px solid #374151;display:block;margin-top:4px;padding-top:4px">${typeLines}</span>`
              : ''),
          style,
        };
      }

      if (layer?.id === 'displacement-flows' || layer?.id === 'destination-dots') {
        return {
          html:
            `<strong>${object.country}</strong><br/>` +
            `Sudanese refugees: ${object.refugees.toLocaleString()}`,
          style,
        };
      }

      return null;
    },
    [regionLookup]
  );

  // Period label
  const periodLabel = useMemo(() => {
    const d = periods[periodIdx];
    if (!d) return '';
    const dt = new Date(d);
    return dt.toLocaleDateString('en-US', {
      month: 'short',
      year: 'numeric',
    });
  }, [periods, periodIdx]);

  // Aggregate totals for current period display
  const periodTotals = useMemo(() => {
    const ev = scatterData.reduce((s, d) => s + d.events, 0);
    const fat = scatterData.reduce((s, d) => s + d.fatalities, 0);
    return { events: ev, fatalities: fat };
  }, [scatterData]);

  return (
    <div className="bg-gray-900 rounded-lg p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-300">
          Crisis Severity by State
        </h3>
        <div className="flex gap-1 text-[10px]">
          {[
            ['severity', 'Severity'],
            ['events', 'Events'],
            ['flows', 'Flows'],
            ['all', 'All'],
          ].map(([mode, label]) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-2 py-1 rounded transition-colors ${
                viewMode === mode
                  ? 'bg-brand-teal/20 text-brand-teal'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Map */}
      <div
        className="rounded-lg overflow-hidden"
        style={{ height: 420 }}
      >
        <Map
          initialViewState={INITIAL_VIEW}
          mapStyle={DARK_BASEMAP}
          style={{ width: '100%', height: '100%' }}
          attributionControl={false}
        >
          <DeckGLOverlay
            layers={layers}
            getTooltip={getTooltip}
          />
        </Map>
      </div>

      {/* Time controls */}
      {(viewMode === 'events' || viewMode === 'all') &&
        periods.length > 0 && (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  if (isPlaying) {
                    setIsPlaying(false);
                  } else {
                    if (periodIdx >= periods.length - 1) {
                      setPeriodIdx(0);
                    }
                    setIsPlaying(true);
                  }
                }}
                className="w-6 h-6 flex items-center justify-center text-brand-teal hover:text-brand-teal/80 transition-colors text-xs"
                title={isPlaying ? 'Pause' : 'Play'}
              >
                {isPlaying ? '\u23F8' : '\u25B6'}
              </button>
              <input
                type="range"
                min={0}
                max={periods.length - 1}
                value={periodIdx >= 0 ? periodIdx : 0}
                onChange={(e) => {
                  setIsPlaying(false);
                  setPeriodIdx(Number(e.target.value));
                }}
                className="flex-1 h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer
                  [&::-webkit-slider-thumb]:appearance-none
                  [&::-webkit-slider-thumb]:w-3
                  [&::-webkit-slider-thumb]:h-3
                  [&::-webkit-slider-thumb]:rounded-full
                  [&::-webkit-slider-thumb]:bg-brand-teal
                  [&::-webkit-slider-thumb]:cursor-pointer"
              />
              <span className="text-xs text-gray-400 w-24 text-right font-medium">
                {periodLabel}
              </span>
            </div>

            {/* Period stats + event type filters */}
            <div className="flex items-center justify-between">
              <div className="flex gap-3 text-[10px]">
                {Object.entries(EVENT_TYPE_LABELS).map(
                  ([key, label]) => (
                    <label
                      key={key}
                      className="flex items-center gap-1.5 cursor-pointer select-none"
                    >
                      <span
                        className="w-2.5 h-2.5 rounded-sm transition-colors"
                        style={{
                          background: activeTypes.has(key)
                            ? `rgb(${EVENT_TYPE_COLORS[key].join(',')})`
                            : '#374151',
                        }}
                        onClick={() => {
                          setActiveTypes((prev) => {
                            const next = new Set(prev);
                            if (next.has(key)) next.delete(key);
                            else next.add(key);
                            return next;
                          });
                        }}
                      />
                      <span
                        className={
                          activeTypes.has(key)
                            ? 'text-gray-300'
                            : 'text-gray-600'
                        }
                        onClick={() => {
                          setActiveTypes((prev) => {
                            const next = new Set(prev);
                            if (next.has(key)) next.delete(key);
                            else next.add(key);
                            return next;
                          });
                        }}
                      >
                        {label}
                      </span>
                    </label>
                  )
                )}
              </div>
              <div className="text-[10px] text-gray-500 tabular-nums">
                {periodTotals.events.toLocaleString()} events
                {' / '}
                {periodTotals.fatalities.toLocaleString()} fatalities
              </div>
            </div>
          </div>
        )}

      {/* Severity legend */}
      <div className="flex items-center gap-4 mt-3 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded"
            style={{ background: '#14b8a6' }}
          />{' '}
          Low
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded"
            style={{ background: '#f59e0b' }}
          />{' '}
          Moderate
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded"
            style={{ background: '#f97316' }}
          />{' '}
          High
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded"
            style={{ background: '#ef4444' }}
          />{' '}
          Critical
        </span>
        <span className="flex items-center gap-1">
          <span
            className="w-3 h-3 rounded"
            style={{ background: '#7f1d1d' }}
          />{' '}
          Catastrophic
        </span>
      </div>
    </div>
  );
}
