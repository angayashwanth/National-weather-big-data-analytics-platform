import React, { useState, useEffect, useCallback } from 'react';
import { EVENT_CATEGORIES, STATUS_CONFIG } from '../constants';
import {
  Lock,
  User,
  Key,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  BarChart3,
  RefreshCw,
  LogOut,
  MapPin,
  Calendar,
  Sparkles,
  Loader2,
  FileText,
  Percent,
  Check,
  X,
  Layers,
  CloudRain,
  CloudLightning,
  Waves,
  Flame,
  CloudFog,
  Wind,
  Compass,
  Image as ImageIcon,
  Film,
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

export function AdminReviewScreen({
  token,
  setToken,
  onReportDecision,
}) {
  // Login form state
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('changeme');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState('');

  // Queue & KPI state
  const [queue, setQueue] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [loadingData, setLoadingData] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [notesState, setNotesState] = useState({});
  const [decisionFeedback, setDecisionFeedback] = useState(null);

  // Handle Login
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError('');

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        throw new Error('Invalid username or password.');
      }

      const data = await res.json();
      // Store token in memory only
      setToken(data.access_token);
    } catch (err) {
      setLoginError(err.message || 'Login failed.');
    } finally {
      setLoginLoading(false);
    }
  };

  // Logout (clears token from memory)
  const handleLogout = () => {
    setToken(null);
    setQueue([]);
    setKpis(null);
  };

  // Fetch queue and KPIs
  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoadingData(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };

      const [queueRes, kpiRes] = await Promise.all([
        fetch('/api/admin/queue', { headers }),
        fetch('/api/admin/kpis', { headers }),
      ]);

      if (queueRes.status === 401 || kpiRes.status === 401) {
        // Token expired or invalid
        setToken(null);
        return;
      }

      if (queueRes.ok) {
        const queueData = await queueRes.json();
        setQueue(queueData);
      }

      if (kpiRes.ok) {
        const kpiData = await kpiRes.json();
        setKpis(kpiData);
      }
    } catch (err) {
      console.error('Error fetching admin data:', err);
    } finally {
      setLoadingData(false);
    }
  }, [token, setToken]);

  useEffect(() => {
    if (token) {
      fetchData();
    }
  }, [token, fetchData]);

  // Handle Verify or Reject
  const handleDecision = async (reportId, status) => {
    if (!token) return;
    setActionLoadingId(reportId);

    try {
      const headers = {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      };
      const note = notesState[reportId] || '';

      const res = await fetch(`/api/admin/reports/${reportId}/decision`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          status,
          notes: note || null,
        }),
      });

      if (!res.ok) {
        throw new Error(`Decision failed with status ${res.status}`);
      }

      const updatedReport = await res.json();

      // Remove from queue
      setQueue((prev) => prev.filter((r) => r.id !== reportId));

      // Show feedback
      setDecisionFeedback({
        id: reportId,
        status,
        message: `Report #${reportId} (${updatedReport.city}) marked as ${status.toUpperCase()}!`,
      });
      setTimeout(() => setDecisionFeedback(null), 4000);

      // Refresh KPIs
      fetchData();

      // Trigger callback if provided
      if (onReportDecision) {
        onReportDecision(updatedReport);
      }
    } catch (err) {
      console.error('Decision error:', err);
      alert(`Action failed: ${err.message}`);
    } finally {
      setActionLoadingId(null);
    }
  };

  // If not logged in, render login form
  if (!token) {
    return (
      <div className="flex-1 overflow-y-auto p-4 flex items-center justify-center bg-slate-950 text-slate-100">
        <div className="w-full max-w-md bg-slate-900/90 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/60 space-y-6">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-amber-600 to-rose-600 flex items-center justify-center mx-auto shadow-lg shadow-amber-500/20">
              <ShieldAlert className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Admin &amp; Meteorologist Login
            </h2>
            <p className="text-xs text-slate-400">
              JWT authenticated review queue. High-impact alerts require human sign-off before public broadcast.
            </p>
          </div>

          {loginError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-slate-400" />
                Username
              </label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-amber-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-slate-400" />
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-amber-500 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full py-2.5 rounded-lg bg-gradient-to-r from-amber-600 to-rose-600 hover:from-amber-500 hover:to-rose-500 text-white font-semibold text-xs flex items-center justify-center gap-2 cursor-pointer transition-all shadow-lg shadow-amber-600/20 disabled:opacity-50"
            >
              {loginLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <Lock className="w-4 h-4" />
                  <span>Authenticate (In-Memory Bearer Token)</span>
                </>
              )}
            </button>
          </form>

          <div className="border-t border-slate-800/80 pt-3 flex items-center justify-between text-[11px] text-slate-500">
            <span>Default credentials:</span>
            <button
              type="button"
              onClick={() => {
                setUsername('admin');
                setPassword('changeme');
              }}
              className="text-amber-400 hover:underline cursor-pointer font-mono"
            >
              admin / changeme
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Logged-in Admin View
  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-slate-950 text-slate-100 flex justify-center">
      <div className="w-full max-w-5xl space-y-6">
        {/* Admin Header with Logout */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-mono text-[11px] border border-amber-500/30 font-semibold">
                ADMIN CONSOLE
              </span>
              <span className="text-xs text-slate-400">• Authenticated as Operator ({username})</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              Human Review &amp; Safety Queue
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={fetchData}
              disabled={loadingData}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingData ? 'animate-spin text-amber-400' : ''}`} />
              <span>Refresh</span>
            </button>

            <button
              type="button"
              onClick={handleLogout}
              className="px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/30 hover:bg-rose-500/20 text-rose-400 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>

        {/* Feedback Alert */}
        {decisionFeedback && (
          <div className={`p-3 rounded-lg text-xs font-semibold flex items-center justify-between border ${
            decisionFeedback.status === 'verified'
              ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
              : 'bg-rose-500/15 border-rose-500/40 text-rose-300'
          }`}>
            <span>{decisionFeedback.message}</span>
            <button
              onClick={() => setDecisionFeedback(null)}
              className="text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* KPI Tiles from /api/admin/kpis */}
        {kpis && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Total Reports */}
            <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-xl">
              <span className="text-[11px] text-slate-400 font-medium block mb-1">Total Reports</span>
              <span className="text-xl font-bold font-mono text-white">{kpis.total_reports}</span>
            </div>

            {/* In Review Queue */}
            <div className="bg-amber-950/20 border border-amber-800/40 p-3 rounded-xl">
              <span className="text-[11px] text-amber-400 font-medium block mb-1">Review Queue</span>
              <span className="text-xl font-bold font-mono text-amber-400">{kpis.by_status?.under_review || 0}</span>
            </div>

            {/* Verified */}
            <div className="bg-emerald-950/20 border border-emerald-800/40 p-3 rounded-xl">
              <span className="text-[11px] text-emerald-400 font-medium block mb-1">Verified</span>
              <span className="text-xl font-bold font-mono text-emerald-400">{kpis.by_status?.verified || 0}</span>
            </div>

            {/* Rejected */}
            <div className="bg-rose-950/20 border border-rose-800/40 p-3 rounded-xl">
              <span className="text-[11px] text-rose-400 font-medium block mb-1">Rejected</span>
              <span className="text-xl font-bold font-mono text-rose-400">{kpis.by_status?.rejected || 0}</span>
            </div>

            {/* Avg Trust Score */}
            <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-xl">
              <span className="text-[11px] text-slate-400 font-medium block mb-1">Avg Trust</span>
              <span className="text-xl font-bold font-mono text-sky-400">
                {Math.round(kpis.avg_trust_score || 0)}%
              </span>
            </div>

            {/* ML Override Rate */}
            <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-xl">
              <span className="text-[11px] text-slate-400 font-medium block mb-1">Override Rate</span>
              <span className="text-xl font-bold font-mono text-purple-400">
                {Math.round((kpis.override_rate || 0) * 100)}%
              </span>
            </div>
          </div>
        )}

        {/* Review Queue Items */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>Pending Human Verification ({queue.length})</span>
            </h3>
            <span className="text-xs text-slate-400 font-mono">
              High Impact first (FIFO within priority)
            </span>
          </div>

          {queue.length === 0 ? (
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-xl p-8 text-center space-y-2">
              <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
              <div className="font-semibold text-slate-200 text-sm">Review Queue is Clear!</div>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                All submitted reports have either been auto-verified by ML or reviewed by an admin operator.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {queue.map((report) => {
                const eventMeta = EVENT_CATEGORIES.find((c) => c.value === report.event_category) || {
                  label: report.event_category,
                  color: '#38bdf8',
                };
                const EventIcon = EVENT_ICON_MAP[report.event_category] || CloudRain;
                const isActionLoading = actionLoadingId === report.id;

                const dateStr = report.timestamp
                  ? new Date(report.timestamp).toLocaleString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : '';

                return (
                  <div
                    key={report.id}
                    className={`bg-slate-900/90 border rounded-xl p-4 sm:p-5 space-y-4 shadow-xl transition-all ${
                      report.high_impact
                        ? 'border-rose-500/50 bg-rose-950/5 ring-1 ring-rose-500/30'
                        : 'border-slate-800'
                    }`}
                  >
                    {/* Top Row: Tag, ID, Location, Date */}
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                      <div className="flex items-center flex-wrap gap-2">
                        {report.high_impact && (
                          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/50 flex items-center gap-1.5 animate-pulse">
                            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                            HIGH IMPACT • ESCALATED TO HUMAN REVIEW
                          </span>
                        )}

                        <span className="font-mono text-xs font-bold text-sky-400">
                          #{report.id}
                        </span>

                        <div className="flex items-center gap-1 text-white font-semibold text-xs">
                          <MapPin className="w-3.5 h-3.5 text-sky-400" />
                          <span>{report.city}</span>
                          <span className="text-slate-400 font-normal">, {report.state}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span
                          className="px-2 py-0.5 rounded text-[11px] font-medium flex items-center gap-1"
                          style={{
                            backgroundColor: `${eventMeta.color}15`,
                            color: eventMeta.color,
                            border: `1px solid ${eventMeta.color}40`,
                          }}
                        >
                          <EventIcon className="w-3 h-3" />
                          {eventMeta.label}
                        </span>
                        <span>•</span>
                        <span className="text-[11px] flex items-center gap-1 text-slate-400">
                          <Calendar className="w-3 h-3 text-slate-500" />
                          {dateStr}
                        </span>
                      </div>
                    </div>

                    {/* Citizen Text Description */}
                    {report.text && (
                      <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs text-slate-200 leading-relaxed">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mb-1">
                          Observation Text
                        </div>
                        <p>{report.text}</p>
                      </div>
                    )}

                    {/* Media Attachments (Photos & Videos) */}
                    {((report.photos && report.photos.length > 0) ||
                      (report.videos && report.videos.length > 0)) && (
                      <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                        <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold flex items-center justify-between">
                          <span className="flex items-center gap-1.5 text-sky-400">
                            <ImageIcon className="w-3.5 h-3.5" />
                            <span>Photo &amp; Video Evidence ({(report.photos?.length || 0) + (report.videos?.length || 0)})</span>
                          </span>
                          <span className="text-[10px] text-slate-500 font-normal">Click thumbnail to view full media</span>
                        </div>

                        <div className="flex flex-wrap gap-2.5 pt-1">
                          {report.photos &&
                            report.photos.map((photoUrl, pIdx) => (
                              <a
                                key={`admin-photo-${report.id}-${pIdx}`}
                                href={photoUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="group relative block w-20 h-20 rounded-lg overflow-hidden border border-slate-700 hover:border-sky-400 transition-all shadow-sm bg-slate-900 shrink-0"
                                title="Click to view full image in new tab"
                              >
                                <img
                                  src={photoUrl}
                                  alt={`Evidence ${pIdx + 1}`}
                                  className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                                  onError={(e) => {
                                    e.target.style.opacity = '0.4';
                                  }}
                                />
                                <div className="absolute inset-0 bg-slate-950/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-[10px] text-sky-300 font-semibold">
                                  <span>Open ↗</span>
                                </div>
                              </a>
                            ))}

                          {report.videos &&
                            report.videos.map((videoUrl, vIdx) => (
                              <div
                                key={`admin-video-${report.id}-${vIdx}`}
                                className="w-44 rounded-lg overflow-hidden border border-slate-700 bg-black flex flex-col justify-center shrink-0"
                              >
                                <video
                                  src={videoUrl}
                                  controls
                                  preload="metadata"
                                  className="w-full max-h-24 object-cover"
                                />
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                    {/* ML Intelligence Breakdown Row */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                      {/* Trust Score */}
                      <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 block">Trust Score</span>
                        <div className="font-bold font-mono text-sm mt-0.5 flex items-center gap-1">
                          <span
                            className={
                              report.trust_score >= 70
                                ? 'text-emerald-400'
                                : report.trust_score >= 40
                                ? 'text-amber-400'
                                : 'text-rose-400'
                            }
                          >
                            {Math.round(report.trust_score || 0)}%
                          </span>
                        </div>
                      </div>

                      {/* Fake / Misleading Score */}
                      <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 block">Fake Risk Score</span>
                        <div className="font-bold font-mono text-sm mt-0.5 flex items-center gap-1">
                          <span
                            className={
                              (report.fake_score || 0) < 0.3
                                ? 'text-emerald-400'
                                : (report.fake_score || 0) < 0.6
                                ? 'text-amber-400'
                                : 'text-rose-400'
                            }
                          >
                            {report.fake_score != null ? report.fake_score.toFixed(2) : '0.00'}
                          </span>
                          <span className="text-[10px] text-slate-500 font-normal">
                            ({(report.fake_score || 0) >= 0.6 ? 'High Risk' : 'Low Risk'})
                          </span>
                        </div>
                      </div>

                      {/* Classification Confidence */}
                      <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 block">NLP Confidence</span>
                        <div className="font-bold font-mono text-sm text-sky-400 mt-0.5">
                          {report.classify_conf != null ? `${Math.round(report.classify_conf * 100)}%` : 'N/A'}
                        </div>
                      </div>

                      {/* ML Suggested Verdict */}
                      <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                        <span className="text-[10px] text-slate-500 block">ML Suggested Verdict</span>
                        <div className="font-bold font-mono text-sm text-amber-400 uppercase mt-0.5">
                          {report.ml_verdict || 'under_review'}
                        </div>
                      </div>
                    </div>

                    {/* Operator Review Notes & Action Buttons */}
                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-1">
                      <div className="flex-1">
                        <input
                          type="text"
                          placeholder="Optional operator notes (e.g., Confirmed with SDRF / Ground radar)..."
                          value={notesState[report.id] || ''}
                          onChange={(e) =>
                            setNotesState((prev) => ({
                              ...prev,
                              [report.id]: e.target.value,
                            }))
                          }
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-amber-500"
                        />
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {/* Reject Button */}
                        <button
                          type="button"
                          disabled={isActionLoading}
                          onClick={() => handleDecision(report.id, 'rejected')}
                          className="px-4 py-2 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 border border-rose-500/40 font-semibold text-xs flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          <span>Reject</span>
                        </button>

                        {/* Verify & Approve Button */}
                        <button
                          type="button"
                          disabled={isActionLoading}
                          onClick={() => handleDecision(report.id, 'verified')}
                          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-all cursor-pointer shadow-lg shadow-emerald-600/20 disabled:opacity-50"
                        >
                          {isActionLoading ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              <span>Processing...</span>
                            </>
                          ) : (
                            <>
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              <span>Approve &amp; Verify</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
