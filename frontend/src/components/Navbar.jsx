import React from 'react';
import {
  Radio,
  CloudSunRain,
  ShieldAlert,
  CheckCircle,
  Clock,
  XCircle,
  Layers,
  Map as MapIcon,
  Send,
  UserCheck,
} from 'lucide-react';

export function Navbar({
  activeTab,
  setActiveTab,
  wsStatus,
  stats,
  total,
  isDarkMap,
  setIsDarkMap,
}) {
  const isLive = wsStatus === 'connected';

  const tabs = [
    { id: 'dashboard', label: 'Live Dashboard', icon: MapIcon },
    { id: 'report', label: 'Report Weather', icon: Send },
    {
      id: 'admin',
      label: 'Admin Review',
      icon: ShieldAlert,
      badge: stats.under_review > 0 ? stats.under_review : null,
    },
  ];

  return (
    <header className="bg-slate-900/95 border-b border-slate-800 text-slate-100 px-3 sm:px-4 py-2 flex flex-wrap items-center justify-between gap-3 shrink-0 z-20 backdrop-blur-md">
      {/* Left: Brand & Title */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20 shrink-0">
          <CloudSunRain className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-sm sm:text-base tracking-tight text-white flex items-center gap-1.5">
              IMD Weather Platform
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30">
                SIH26069
              </span>
            </h1>
          </div>
          <p className="text-[11px] text-slate-400 hidden xl:block">
            National Big Data Analytics &amp; Automated Verification
          </p>
        </div>
      </div>

      {/* Center: Tab Navigation */}
      <nav className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 shadow-inner">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer select-none ${
                isActive
                  ? 'bg-gradient-to-r from-sky-600 to-indigo-600 text-white shadow-md shadow-sky-600/25'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
              {tab.badge != null && (
                <span
                  className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                    isActive
                      ? 'bg-white/20 text-white'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse'
                  }`}
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Right Controls: KPIs + Map View & WebSocket Status */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Quick status counter for desktop */}
        <div className="hidden 2xl:flex items-center gap-2 text-xs">
          <div className="px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-800/40 text-emerald-400 font-mono">
            {stats.verified} Verified
          </div>
          <div className="px-2 py-0.5 rounded bg-amber-950/40 border border-amber-800/40 text-amber-400 font-mono">
            {stats.under_review} Queue
          </div>
        </div>

        {/* Dark map tone toggle (only shown on dashboard tab) */}
        {activeTab === 'dashboard' && (
          <button
            onClick={() => setIsDarkMap((prev) => !prev)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium border flex items-center gap-1.5 transition-colors cursor-pointer ${
              isDarkMap
                ? 'bg-slate-800 text-sky-300 border-sky-500/40'
                : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
            title="Toggle Dark/Natural Map Tile Style"
          >
            <Layers className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{isDarkMap ? 'Dark Map' : 'Natural Map'}</span>
          </button>
        )}

        {/* WebSocket Live Status Indicator */}
        <div
          className={`flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold tracking-wide border transition-all ${
            isLive
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : wsStatus === 'connecting'
              ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
              : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
          }`}
          title={
            isLive
              ? 'Real-time WebSocket stream active (/ws)'
              : `Connection status: ${wsStatus}`
          }
        >
          <span className="relative flex h-2 w-2">
            {isLive && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            )}
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isLive
                  ? 'bg-emerald-400'
                  : wsStatus === 'connecting'
                  ? 'bg-amber-400'
                  : 'bg-rose-500'
              }`}
            ></span>
          </span>
          <span className="font-mono text-[11px]">
            {isLive ? 'LIVE FEED' : wsStatus === 'connecting' ? 'CONNECTING...' : 'OFFLINE'}
          </span>
        </div>
      </div>
    </header>
  );
}
