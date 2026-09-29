import React from 'react';
import { EVENT_CATEGORIES, STATUS_CONFIG, INDIAN_STATES } from '../constants';
import { Filter, RotateCcw, Calendar, MapPin, Tag, ShieldCheck, Search } from 'lucide-react';

export function FilterPanel({ filters, setFilters, onReset, statesInReports = [] }) {
  // Combine predefined states with any detected in current reports
  const allStates = Array.from(new Set([...INDIAN_STATES, ...statesInReports]))
    .filter(Boolean)
    .sort();

  const activeCount = [
    filters.event,
    filters.status,
    filters.state,
    filters.dateFrom,
    filters.dateTo,
    filters.city,
  ].filter(Boolean).length;

  const handleChange = (key, value) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  return (
    <div className="bg-slate-900/90 border-b border-slate-800 p-3 text-xs text-slate-200">
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-1.5 font-semibold text-slate-300">
          <Filter className="w-3.5 h-3.5 text-sky-400" />
          <span>Filters</span>
          {activeCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full bg-sky-500/20 text-sky-400 font-mono text-[10px] border border-sky-500/30">
              {activeCount} active
            </span>
          )}
        </div>
        {activeCount > 0 && (
          <button
            onClick={onReset}
            className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-sky-400 transition-colors cursor-pointer"
            title="Reset all filters"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        {/* Event Type Filter */}
        <div className="col-span-1">
          <label className="block text-[11px] text-slate-400 mb-1 flex items-center gap-1">
            <Tag className="w-3 h-3 text-slate-400" />
            <span>Event Category</span>
          </label>
          <select
            value={filters.event || ''}
            onChange={(e) => handleChange('event', e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-sky-500 transition-colors"
          >
            <option value="">All Events</option>
            {EVENT_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        {/* Verification Status Filter */}
        <div className="col-span-1">
          <label className="block text-[11px] text-slate-400 mb-1 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-slate-400" />
            <span>Status</span>
          </label>
          <select
            value={filters.status || ''}
            onChange={(e) => handleChange('status', e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-sky-500 transition-colors"
          >
            <option value="">All Statuses</option>
            {Object.entries(STATUS_CONFIG).map(([key, val]) => (
              <option key={key} value={key}>
                {val.label}
              </option>
            ))}
          </select>
        </div>

        {/* State Filter */}
        <div className="col-span-1">
          <label className="block text-[11px] text-slate-400 mb-1 flex items-center gap-1">
            <MapPin className="w-3 h-3 text-slate-400" />
            <span>State</span>
          </label>
          <select
            value={filters.state || ''}
            onChange={(e) => handleChange('state', e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-sky-500 transition-colors"
          >
            <option value="">All States</option>
            {allStates.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </div>

        {/* City Filter */}
        <div className="col-span-1">
          <label className="block text-[11px] text-slate-400 mb-1 flex items-center gap-1">
            <Search className="w-3 h-3 text-slate-400" />
            <span>City Search</span>
          </label>
          <input
            type="text"
            placeholder="e.g. Mumbai, Delhi"
            value={filters.city || ''}
            onChange={(e) => handleChange('city', e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-colors"
          />
        </div>

        {/* Date From */}
        <div className="col-span-1">
          <label className="block text-[11px] text-slate-400 mb-1 flex items-center gap-1">
            <Calendar className="w-3 h-3 text-slate-400" />
            <span>Date From</span>
          </label>
          <input
            type="date"
            value={filters.dateFrom || ''}
            onChange={(e) => handleChange('dateFrom', e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-sky-500 transition-colors"
          />
        </div>

        {/* Date To */}
        <div className="col-span-1">
          <label className="block text-[11px] text-slate-400 mb-1 flex items-center gap-1">
            <Calendar className="w-3 h-3 text-slate-400" />
            <span>Date To</span>
          </label>
          <input
            type="date"
            value={filters.dateTo || ''}
            onChange={(e) => handleChange('dateTo', e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-sky-500 transition-colors"
          />
        </div>
      </div>
    </div>
  );
}
