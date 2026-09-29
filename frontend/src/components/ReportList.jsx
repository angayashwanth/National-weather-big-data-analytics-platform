import React from 'react';
import { ReportCard } from './ReportCard';
import { ListFilter, Loader2, AlertCircle } from 'lucide-react';

export function ReportList({
  reports,
  loading,
  error,
  selectedReportId,
  onSelectReport,
}) {
  if (loading && reports.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400 gap-2">
        <Loader2 className="w-6 h-6 animate-spin text-sky-400" />
        <span className="text-xs">Loading weather reports...</span>
      </div>
    );
  }

  if (error && reports.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-rose-400 gap-2 text-center">
        <AlertCircle className="w-6 h-6" />
        <span className="text-xs font-medium">{error}</span>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-slate-950/40">
      {/* Header bar */}
      <div className="px-3 py-2 bg-slate-900/60 border-b border-slate-800/80 flex items-center justify-between text-xs text-slate-400 shrink-0">
        <div className="flex items-center gap-1.5 font-medium">
          <ListFilter className="w-3.5 h-3.5 text-slate-400" />
          <span>Weather Reports ({reports.length})</span>
        </div>
        <span className="text-[11px] text-slate-500 font-mono">
          Click item to view on map
        </span>
      </div>

      {/* Reports Scroll Area */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
        {reports.length === 0 ? (
          <div className="h-40 flex flex-col items-center justify-center text-center p-4 text-slate-500 text-xs">
            <p className="font-medium text-slate-400 mb-1">No reports match current filters</p>
            <p className="text-[11px]">Try adjusting the event category, status, or date range.</p>
          </div>
        ) : (
          reports.map((report) => (
            <ReportCard
              key={report.id}
              report={report}
              isSelected={selectedReportId === report.id}
              onClick={onSelectReport}
            />
          ))
        )}
      </div>
    </div>
  );
}
