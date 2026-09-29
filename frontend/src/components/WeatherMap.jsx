import React, { useEffect, useRef, useCallback } from 'react';
import * as maplibregl from 'maplibre-gl';
import { MAP_CENTER_INDIA, MAP_DEFAULT_ZOOM, EVENT_CATEGORIES, STATUS_CONFIG, SOURCE_TYPE_LABELS } from '../constants';

export function WeatherMap({
  reports,
  selectedReport,
  onSelectReport,
  isDarkMap,
}) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const popupRef = useRef(null);

  // Convert reports list with valid GPS to GeoJSON FeatureCollection
  const getGeoJsonData = useCallback((items) => {
    const features = items
      .filter(
        (r) =>
          r.gps_location &&
          r.gps_location.latitude != null &&
          r.gps_location.longitude != null &&
          !isNaN(r.gps_location.latitude) &&
          !isNaN(r.gps_location.longitude)
      )
      .map((r) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [r.gps_location.longitude, r.gps_location.latitude],
        },
        properties: {
          id: r.id,
          city: r.city,
          state: r.state,
          event_category: r.event_category,
          verification_status: r.verification_status,
          trust_score: r.trust_score,
          timestamp: r.timestamp,
          text: r.text || '',
          source_type: r.source_type,
          high_impact: r.high_impact ? 1 : 0,
          photos: Array.isArray(r.photos) ? r.photos.join(',') : (r.photos || ''),
          videos: Array.isArray(r.videos) ? r.videos.join(',') : (r.videos || ''),
        },
      }));

    return {
      type: 'FeatureCollection',
      features,
    };
  }, []);

  // Format popup HTML for a report
  const createPopupHtml = (props) => {
    const statusCfg = STATUS_CONFIG[props.verification_status] || STATUS_CONFIG.unverified;
    const eventCfg = EVENT_CATEGORIES.find((e) => e.value === props.event_category) || {
      label: props.event_category,
      color: '#38bdf8',
    };
    const sourceLabel = SOURCE_TYPE_LABELS[props.source_type] || props.source_type || 'Unknown';
    const dateFormatted = props.timestamp
      ? new Date(props.timestamp).toLocaleString(undefined, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : '';

    const photoList = props.photos
      ? String(props.photos)
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
      : [];
    const videoList = props.videos
      ? String(props.videos)
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
      : [];

    return `
      <div style="font-family: inherit; color: #f1f5f9; padding: 4px 2px;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px;">
          <div style="font-weight: 700; font-size: 14px; color: #ffffff;">
            ${props.city}, <span style="font-weight: normal; color: #94a3b8; font-size: 12px;">${props.state}</span>
          </div>
          <span style="font-size: 10px; font-weight: 600; text-transform: uppercase; padding: 2px 7px; border-radius: 9999px; background-color: ${statusCfg.color}25; color: ${statusCfg.color}; border: 1px solid ${statusCfg.color}40;">
            ${statusCfg.label}
          </span>
        </div>

        <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
          <span style="font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background-color: ${eventCfg.color}20; color: ${eventCfg.color}; border: 1px solid ${eventCfg.color}40;">
            ${eventCfg.label}
          </span>
          ${
            props.high_impact
              ? `<span style="font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background-color: #ef444430; color: #f87171; border: 1px solid #ef444460;">HIGH IMPACT</span>`
              : ''
          }
          <span style="font-size: 10px; color: #64748b; margin-left: auto;">${dateFormatted}</span>
        </div>

        ${
          props.text
            ? `<div style="font-size: 11px; color: #cbd5e1; background: #020617; border: 1px solid #1e293b; padding: 6px 8px; border-radius: 6px; margin-bottom: 8px; line-height: 1.4;">
                ${props.text}
               </div>`
            : ''
        }

        ${
          photoList.length > 0
            ? `<div style="margin-bottom: 8px;">
                <div style="font-size: 10px; color: #94a3b8; font-weight: 600; margin-bottom: 4px;">
                  📸 PHOTO EVIDENCE (${photoList.length}):
                </div>
                <div style="display: flex; gap: 6px; overflow-x: auto; padding-bottom: 4px; max-width: 260px;">
                  ${photoList
                    .map(
                      (url) =>
                        `<a href="${url}" target="_blank" rel="noopener noreferrer" title="Click to view full image" style="display: block; flex-shrink: 0;">
                          <img src="${url}" alt="Observation thumbnail" style="width: 58px; height: 58px; object-fit: cover; border-radius: 6px; border: 1px solid #334155; background: #0f172a;" onerror="this.style.display='none'" />
                        </a>`
                    )
                    .join('')}
                </div>
              </div>`
            : ''
        }

        ${
          videoList.length > 0
            ? `<div style="margin-bottom: 8px;">
                <div style="font-size: 10px; color: #94a3b8; font-weight: 600; margin-bottom: 4px;">
                  🎥 VIDEO EVIDENCE (${videoList.length}):
                </div>
                <div style="display: flex; gap: 6px; overflow-x: auto; max-width: 260px;">
                  ${videoList
                    .map(
                      (url) =>
                        `<video src="${url}" controls preload="metadata" style="max-width: 220px; max-height: 100px; border-radius: 6px; border: 1px solid #334155; background: #000;"></video>`
                    )
                    .join('')}
                </div>
              </div>`
            : ''
        }

        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 10px; color: #94a3b8; border-top: 1px solid #1e293b; pt: 6px; padding-top: 6px;">
          <span>Source: <strong style="color: #e2e8f0;">${sourceLabel}</strong></span>
          <span>Trust: <strong style="color: ${props.trust_score >= 70 ? '#4ade80' : '#fbbf24'}; font-family: monospace;">${Math.round(props.trust_score || 0)}%</strong></span>
        </div>
      </div>
    `;
  };

  // Initialize MapLibre GL map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Base OSM raster style
    const mapStyle = {
      version: 8,
      sources: {
        'osm-tiles': {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '&copy; OpenStreetMap contributors',
        },
      },
      layers: [
        {
          id: 'background',
          type: 'background',
          paint: {
            'background-color': '#090d16',
          },
        },
        {
          id: 'osm-layer',
          type: 'raster',
          source: 'osm-tiles',
          minzoom: 0,
          maxzoom: 19,
        },
      ],
    };

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: mapStyle,
      center: MAP_CENTER_INDIA,
      zoom: MAP_DEFAULT_ZOOM,
      attributionControl: true,
    });

    mapRef.current = map;

    // Controls
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right');

    map.on('load', () => {
      // Add GeoJSON source for weather reports
      map.addSource('reports-geojson', {
        type: 'geojson',
        data: getGeoJsonData(reports),
      });

      // 1. Heatmap layer - active at lower zoom levels, fading out around zoom 7.5
      map.addLayer({
        id: 'reports-heat',
        type: 'heatmap',
        source: 'reports-geojson',
        maxzoom: 8,
        paint: {
          'heatmap-weight': [
            'interpolate',
            ['linear'],
            ['get', 'trust_score'],
            0, 0.3,
            100, 1.0,
          ],
          'heatmap-intensity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            0, 1,
            8, 3,
          ],
          'heatmap-color': [
            'interpolate',
            ['linear'],
            ['heatmap-density'],
            0, 'rgba(0, 0, 255, 0)',
            0.2, 'rgba(56, 189, 248, 0.6)',
            0.4, 'rgba(52, 211, 153, 0.7)',
            0.6, 'rgba(251, 191, 36, 0.8)',
            0.8, 'rgba(249, 115, 22, 0.9)',
            1.0, 'rgba(239, 68, 68, 0.95)',
          ],
          'heatmap-radius': [
            'interpolate',
            ['linear'],
            ['zoom'],
            0, 6,
            5, 18,
            8, 35,
          ],
          'heatmap-opacity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            5.5, 0.9,
            7.5, 0.05,
          ],
        },
      });

      // 2. High-impact pulse halo for extreme alerts
      map.addLayer({
        id: 'reports-pulse',
        type: 'circle',
        source: 'reports-geojson',
        minzoom: 5,
        filter: ['==', ['get', 'high_impact'], 1],
        paint: {
          'circle-radius': [
            'interpolate',
            ['linear'],
            ['zoom'],
            5, 12,
            8, 18,
            14, 24,
          ],
          'circle-color': '#ef4444',
          'circle-opacity': 0.25,
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#f87171',
          'circle-stroke-opacity': 0.6,
        },
      });

      // 3. Status-coloured circle markers - active when zooming in
      map.addLayer({
        id: 'reports-circles',
        type: 'circle',
        source: 'reports-geojson',
        minzoom: 5,
        paint: {
          'circle-color': [
            'match',
            ['get', 'verification_status'],
            'verified', '#22c55e',      // Green
            'under_review', '#f59e0b',  // Amber
            'rejected', '#ef4444',      // Red
            'unverified', '#9ca3af',    // Grey
            '#38bdf8',                  // default sky blue
          ],
          'circle-radius': [
            'interpolate',
            ['linear'],
            ['zoom'],
            5, 6,
            8, 9,
            12, 13,
          ],
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff',
          'circle-opacity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            5, 0.4,
            6.5, 1,
          ],
          'circle-stroke-opacity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            5, 0.4,
            6.5, 1,
          ],
        },
      });

      // Marker click -> popup
      map.on('click', 'reports-circles', (e) => {
        if (!e.features || !e.features[0]) return;
        const feature = e.features[0];
        const coordinates = feature.geometry.coordinates.slice();
        const properties = feature.properties;

        if (onSelectReport) {
          onSelectReport(properties);
        }

        if (popupRef.current) {
          popupRef.current.remove();
        }

        popupRef.current = new maplibregl.Popup({
          closeButton: true,
          closeOnClick: false,
          offset: 14,
        })
          .setLngLat(coordinates)
          .setHTML(createPopupHtml(properties))
          .addTo(map);
      });

      // Cursor changes on hover
      map.on('mouseenter', 'reports-circles', () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', 'reports-circles', () => {
        map.getCanvas().style.cursor = '';
      });
    });

    // Cleanup
    return () => {
      if (popupRef.current) popupRef.current.remove();
      map.remove();
    };
  }, []);

  // Update GeoJSON source when reports change
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;
    if (!map.isStyleLoaded()) return;

    const source = map.getSource('reports-geojson');
    if (source) {
      source.setData(getGeoJsonData(reports));
    }
  }, [reports, getGeoJsonData]);

  // Handle fly-to when selectedReport changes
  useEffect(() => {
    if (!mapRef.current || !selectedReport) return;
    const map = mapRef.current;

    const lat = selectedReport.gps_location?.latitude ?? selectedReport.latitude;
    const lon = selectedReport.gps_location?.longitude ?? selectedReport.longitude;

    if (lat != null && lon != null && !isNaN(lat) && !isNaN(lon)) {
      map.flyTo({
        center: [lon, lat],
        zoom: Math.max(map.getZoom(), 8.5),
        essential: true,
        duration: 1200,
      });

      if (popupRef.current) {
        popupRef.current.remove();
      }

      // Open popup on marker
      popupRef.current = new maplibregl.Popup({
        closeButton: true,
        closeOnClick: false,
        offset: 14,
      })
        .setLngLat([lon, lat])
        .setHTML(
          createPopupHtml({
            city: selectedReport.city,
            state: selectedReport.state,
            event_category: selectedReport.event_category,
            verification_status: selectedReport.verification_status,
            trust_score: selectedReport.trust_score,
            timestamp: selectedReport.timestamp,
            text: selectedReport.text,
            source_type: selectedReport.source_type,
            high_impact: selectedReport.high_impact ? 1 : 0,
          })
        )
        .addTo(map);
    }
  }, [selectedReport]);

  // Resize map when sidebar or window layout changes
  useEffect(() => {
    const handleResize = () => {
      if (mapRef.current) {
        mapRef.current.resize();
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="relative w-full h-full flex-1 min-h-[350px] bg-slate-950 overflow-hidden">
      {/* Map container with dynamic dark/natural tile class */}
      <div
        ref={mapContainerRef}
        className={`w-full h-full ${isDarkMap ? 'dark-map-tiles' : ''}`}
      />

      {/* Map Legend Overlay */}
      <div className="absolute bottom-4 right-4 bg-slate-900/90 backdrop-blur-md border border-slate-800 p-2.5 rounded-lg text-[11px] text-slate-300 shadow-xl pointer-events-auto z-10 hidden sm:block">
        <div className="font-semibold text-xs text-white mb-1.5 flex items-center justify-between gap-4">
          <span>Map Legend</span>
          <span className="text-[10px] text-slate-400 font-normal">Zoom in for markers</span>
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#22c55e] inline-block border border-white/80"></span>
            <span>Verified</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#f59e0b] inline-block border border-white/80"></span>
            <span>Under Review</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#ef4444] inline-block border border-white/80"></span>
            <span>Rejected</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#9ca3af] inline-block border border-white/80"></span>
            <span>Unverified</span>
          </div>
        </div>
        <div className="border-t border-slate-800 mt-2 pt-1.5 text-[10px] text-slate-400 flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
          <span>Red halo = High Impact Event</span>
        </div>
      </div>
    </div>
  );
}
