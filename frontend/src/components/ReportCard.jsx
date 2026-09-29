import React from 'react';
import { StatusBadge } from './StatusBadge';
import { EVENT_CATEGORIES, SOURCE_TYPE_LABELS } from '../constants';
import {
  MapPin,
  Calendar,
  ShieldAlert,
  Image as ImageIcon,
  AlertTriangle,
  Radio,
  Share2,
  FileText,
  CloudRain,
  CloudLightning,
  Waves,
  Flame,
  CloudFog,
  Wind,
  Compass,
} from 'lucide-react';

const EVENT_ICON_MAP = {
  rainfall: CloudRain,
  thunderstorm: CloudLightning,
  flooding: Waves,
  heatwave: Flame,
  fog: CloudFog,
  dust_storm: Wind,
  strong_wind: Compass,
};

export function ReportCard({ report, isSelected, onClick }) {
  const eventMeta = EVENT_CATEGORIES.find((c) => c.value === report.event_category) || {
    label: report.event_category,
    color: '#38bdf8',
  };
  const EventIcon = EVENT_ICON_MAP[report.event_category] || CloudRain;

  const hasGps =
    report.gps_location?.latitude != null && report.gps_location?.longitude != null;

  // Format date
  const dateStr = report.timestamp
    ? new Date(report.timestamp).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Unknown time';

  return (
    <div
      onClick={() => onClick(report)}
      className={`p-3 rounded-lg border transition-all cursor-pointer select-none text-xs relative ${
        isSelected
          ? 'bg-slate-800/90 border-sky-500 shadow-md shadow-sky-500/10 ring-1 ring-sky-500/50'
          : 'bg-slate-900/60 border-slate-800/80 hover:bg-slate-800/60 hover:border-slate-700'
      }`}
    >
      {/* Top Row: Location & Status */}
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5 font-semibold text-slate-100 text-sm">
          <MapPin className="w-3.5 h-3.5 text-sky-400 shrink-0" />
          <span className="truncate">{report.city}</span>
          <span className="text-slate-400 font-normal text-xs">, {report.state}</span>
        </div>
        <StatusBadge status={report.verification_status} size="xs" />
      </div>

      {/* Second Row: Event Category Pill & High Impact alert */}
      <div className="flex items-center flex-wrap gap-1.5 mb-2">
        <span
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium"
          style={{
            backgroundColor: `${eventMeta.color}15`,
            color: eventMeta.color,
            border: `1px solid ${eventMeta.color}40`,
          }}
        >
          <EventIcon className="w-3 h-3" />
          {eventMeta.label}
        </span>

        {report.high_impact && (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">
            <AlertTriangle className="w-2.5 h-2.5" />
            HIGH IMPACT
          </span>
        )}

        <span className="text-[10px] text-slate-400 ml-auto flex items-center gap-1">
          <Calendar className="w-3 h-3 text-slate-500" />
          {dateStr}
        </span>
      </div>

      {/* Description Snippet & Photo Thumbnail if present */}
      {(report.text || (report.photos && report.photos.length > 0)) && (
        <div className="flex items-start gap-2 mb-2">
          {report.photos && report.photos.length > 0 && (
            <img
              src={report.photos[0]}
              alt="Evidence thumbnail"
              className="w-11 h-11 rounded object-cover border border-slate-700 shrink-0 bg-slate-950"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          )}
          {report.text && (
            <p className="text-slate-300 line-clamp-2 text-[11px] leading-relaxed bg-slate-950/40 p-1.5 rounded border border-slate-800/40 flex-1">
              {report.text}
            </p>
          )}
        </div>
      )}

      {/* Bottom Row: Metadata tags */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 border-t border-slate-800/60 pt-1.5 mt-1">
        <div className="flex items-center gap-2">
          <span className="text-slate-400">
            {SOURCE_TYPE_LABELS[report.source_type] || report.source_type}
          </span>
          {report.photos && report.photos.length > 0 && (
            <span className="flex items-center gap-0.5 text-sky-400" title="Includes photo evidence">
              <ImageIcon className="w-2.5 h-2.5" />
              <span>{report.photos.length}</span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Trust Score */}
          <div className="flex items-center gap-1" title="Trust Score">
            <span className="text-slate-500">Trust:</span>
            <span
              className={`font-mono font-medium ${
                report.trust_score >= 70
                  ? 'text-emerald-400'
                  : report.trust_score >= 40
                  ? 'text-amber-400'
                  : 'text-rose-400'
              }`}
            >
              {Math.round(report.trust_score || 0)}%
            </span>
          </div>

          {/* GPS status */}
          <span
            className={`font-mono text-[9px] px-1 py-0.2 rounded border ${
              hasGps
                ? 'bg-sky-500/10 text-sky-400 border-sky-500/30'
                : 'bg-slate-800 text-slate-500 border-slate-700'
            }`}
          >
            {hasGps ? 'GPS' : 'NO GPS'}
          </span>
        </div>
      </div>
    </div>
  );
}
