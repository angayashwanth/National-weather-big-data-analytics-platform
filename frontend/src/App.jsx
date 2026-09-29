import React, { useState, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { FilterPanel } from './components/FilterPanel';
import { ReportList } from './components/ReportList';
import { WeatherMap } from './components/WeatherMap';
import { CitizenReportScreen } from './components/CitizenReportScreen';
import { AdminReviewScreen } from './components/AdminReviewScreen';
import { useReports } from './hooks/useReports';
import { useWebSocket } from './hooks/useWebSocket';
import { CheckCircle2, X } from 'lucide-react';

export default function App() {
  // Tab state: 'dashboard' | 'report' | 'admin'
  const [activeTab, setActiveTab] = useState('dashboard');

  // In-memory admin token (never stored in localStorage or sessionStorage)
  const [adminToken, setAdminToken] = useState(null);

  // Filter states for Live Dashboard
  const [filters, setFilters] = useState({
    dateFrom: '',
    dateTo: '',
    event: '',
    state: '',
    status: '',
    city: '',
  });

  // Selected report to focus on map
  const [selectedReport, setSelectedReport] = useState(null);

  // Map theme styling (dark tiles vs natural OSM)
  const [isDarkMap, setIsDarkMap] = useState(true);

  // Real-time toast state
  const [toast, setToast] = useState(null);

  // Fetch reports from API with filters
  const { reports, total, loading, error, refresh, stats } = useReports(filters);

  // Handle verified reports broadcast via WebSocket
  const handleReportVerified = useCallback(
    (payload) => {
      console.log('[Live Feed] Report verified broadcast:', payload);
      setToast({
        id: Date.now(),
        message: `Report #${payload.report_id} verified in ${payload.city || 'India'} (${payload.event_category || 'Weather Event'})!`,
      });

      // Refresh reports list and map markers without page refresh
      refresh();

      // Auto-dismiss toast after 6 seconds
      setTimeout(() => {
        setToast((current) => (current && current.id === payload.id ? null : current));
      }, 6000);
    },
    [refresh]
  );

  // WebSocket with auto-reconnect and indicator
  const { status: wsStatus } = useWebSocket({
    onReportVerified: handleReportVerified,
  });

  // Unique list of states present in current reports
  const statesInReports = Array.from(new Set(reports.map((r) => r.state))).filter(Boolean);

  const handleResetFilters = () => {
    setFilters({
      dateFrom: '',
      dateTo: '',
      event: '',
      state: '',
      status: '',
      city: '',
    });
    setSelectedReport(null);
  };

  const handleSelectReport = (report) => {
    setSelectedReport(report);
  };

  const handleReportSubmitted = (newReportId) => {
    refresh();
  };

  const handleReportDecision = (updatedReport) => {
    refresh();
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans select-none">
      {/* Top Navigation Bar with Tabs, Live Stats, and WebSocket */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        wsStatus={wsStatus}
        stats={stats}
        total={total}
        isDarkMap={isDarkMap}
        setIsDarkMap={setIsDarkMap}
      />

      {/* Main Body */}
      <main className="flex-1 relative min-h-0 overflow-hidden flex flex-col">
        {/* Screen 1: Live Dashboard (Map + Sidebar) */}
        <div
          className={`flex-1 flex flex-col md:flex-row min-h-0 relative ${
            activeTab === 'dashboard' ? '' : 'hidden'
          }`}
        >
          {/* Left Sidebar: Filters & Report List */}
          <aside className="w-full md:w-96 lg:w-[420px] shrink-0 bg-slate-900/95 border-b md:border-b-0 md:border-r border-slate-800 flex flex-col max-h-[48vh] md:max-h-full z-10 shadow-xl">
            {/* Filters Section */}
            <FilterPanel
              filters={filters}
              setFilters={setFilters}
              onReset={handleResetFilters}
              statesInReports={statesInReports}
            />

            {/* Report List Section */}
            <ReportList
              reports={reports}
              loading={loading}
              error={error}
              selectedReportId={selectedReport?.id}
              onSelectReport={handleSelectReport}
            />
          </aside>

          {/* Right Section: Full-height MapLibre Map */}
          <section className="flex-1 h-full relative overflow-hidden">
            <WeatherMap
              reports={reports}
              selectedReport={selectedReport}
              onSelectReport={handleSelectReport}
              isDarkMap={isDarkMap}
            />
          </section>
        </div>

        {/* Screen 2: Citizen Report Intake */}
        {activeTab === 'report' && (
          <CitizenReportScreen
            onSwitchTab={(tab) => setActiveTab(tab)}
            onReportSubmitted={handleReportSubmitted}
          />
        )}

        {/* Screen 3: Admin Review Queue */}
        {activeTab === 'admin' && (
          <AdminReviewScreen
            token={adminToken}
            setToken={setAdminToken}
            onReportDecision={handleReportDecision}
          />
        )}
      </main>

      {/* Real-Time Live Notification Toast */}
      {toast && (
        <div className="absolute top-16 right-4 z-50 animate-bounce duration-500 max-w-sm bg-slate-900 border border-emerald-500/50 rounded-xl p-3 text-xs text-white shadow-2xl flex items-center gap-2.5">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <div className="flex-1">
            <div className="font-semibold text-emerald-400">Live Verification Broadcast</div>
            <div className="text-slate-300 text-[11px]">{toast.message}</div>
          </div>
          <button
            onClick={() => setToast(null)}
            className="text-slate-400 hover:text-white p-1 cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}
