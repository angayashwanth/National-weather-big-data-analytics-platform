import React, { useState, useEffect, useRef } from 'react';
import { EVENT_CATEGORIES, INDIAN_STATES } from '../constants';
import { StatusBadge } from './StatusBadge';
import {
  Send,
  MapPin,
  Compass,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  Clock,
  Sparkles,
  Loader2,
  Radio,
  FileText,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  CloudRain,
  CloudLightning,
  Waves,
  Flame,
  CloudFog,
  Wind,
  UploadCloud,
  Image as ImageIcon,
  Film,
  Trash2,
  X,
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

export function CitizenReportScreen({ onSwitchTab, onReportSubmitted }) {
  // Form state
  const [category, setCategory] = useState('flooding');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [text, setText] = useState('');
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  
  // Media upload state
  const [uploadedMedia, setUploadedMedia] = useState([]);
  const [uploadingMedia, setUploadingMedia] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const fileInputRef = useRef(null);

  // GPS capture state
  const [gpsStatus, setGpsStatus] = useState('idle'); // idle | locating | success | error
  const [gpsError, setGpsError] = useState('');

  // Submission & Polling state
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [submittedReportId, setSubmittedReportId] = useState(null);
  const [polledReport, setPolledReport] = useState(null);
  const [pollCount, setPollCount] = useState(0);

  const pollIntervalRef = useRef(null);

  // Capture GPS using browser geolocation
  const handleCaptureGps = () => {
    setGpsStatus('locating');
    setGpsError('');

    if (!navigator.geolocation) {
      setGpsStatus('error');
      setGpsError('Geolocation is not supported by your browser.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const latitude = Number(position.coords.latitude.toFixed(6));
        const longitude = Number(position.coords.longitude.toFixed(6));
        setLat(String(latitude));
        setLon(String(longitude));
        setGpsStatus('success');
      },
      (error) => {
        setGpsStatus('error');
        let msg = 'Failed to retrieve location.';
        if (error.code === error.PERMISSION_DENIED) {
          msg = 'Location permission denied by user/browser.';
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          msg = 'Location information is unavailable.';
        } else if (error.code === error.TIMEOUT) {
          msg = 'Location request timed out.';
        }
        setGpsError(msg);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  };

  // Quick preset helper
  const handleApplyPreset = (presetCity, presetState, presetLat, presetLon, presetCategory, presetText) => {
    setCity(presetCity);
    setState(presetState);
    setLat(String(presetLat));
    setLon(String(presetLon));
    setGpsStatus('success');
    if (presetCategory) setCategory(presetCategory);
    if (presetText) setText(presetText);
  };

  // Handle file uploads to POST /api/media
  const handleFileChange = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploadError('');
    setUploadingMedia(true);

    try {
      for (const file of files) {
        if (file.size > 10 * 1024 * 1024) {
          throw new Error(`"${file.name}" exceeds 10 MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`);
        }
        const isImage = file.type.startsWith('image/');
        const isVideo = file.type.startsWith('video/');
        if (!isImage && !isVideo) {
          throw new Error(`"${file.name}" has unsupported format. Only photos and videos allowed.`);
        }

        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch('/api/media', {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Upload failed (${res.status})`);
        }

        const data = await res.json();
        setUploadedMedia((prev) => [
          ...prev,
          {
            url: data.url,
            filename: data.filename || file.name,
            content_type: data.content_type || file.type,
            size_bytes: data.size_bytes || file.size,
            isVideo,
          },
        ]);
      }
    } catch (err) {
      console.error('File upload error:', err);
      setUploadError(err.message || 'Failed to upload media file.');
    } finally {
      setUploadingMedia(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemoveMedia = (indexToRemove) => {
    setUploadedMedia((prev) => prev.filter((_, idx) => idx !== indexToRemove));
  };

  // Submit report
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!category) {
      setSubmitError('Please select a weather event category.');
      return;
    }
    if (!city.trim() || !state.trim()) {
      setSubmitError('City and State are required.');
      return;
    }

    setSubmitting(true);
    setSubmitError('');

    try {
      const photos = uploadedMedia.filter((m) => !m.isVideo).map((m) => m.url);
      const videos = uploadedMedia.filter((m) => m.isVideo).map((m) => m.url);

      const payload = {
        city: city.trim(),
        state: state.trim(),
        lat: lat ? parseFloat(lat) : null,
        lon: lon ? parseFloat(lon) : null,
        event_category: category,
        source_type: 'citizen_report',
        text: text.trim() || null,
        photos,
        videos,
      };

      const res = await fetch('/api/reports', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Submission failed with status ${res.status}`);
      }

      const data = await res.json();
      setSubmittedReportId(data.id);
      setPollCount(0);

      if (onReportSubmitted) {
        onReportSubmitted(data.id);
      }
    } catch (err) {
      console.error('Submit error:', err);
      setSubmitError(err.message || 'Failed to submit report.');
    } finally {
      setSubmitting(false);
    }
  };

  // Poll GET /api/reports/{id} every 2s once submitted
  useEffect(() => {
    if (!submittedReportId) return;

    const fetchReportStatus = async () => {
      try {
        const res = await fetch(`/api/reports/${submittedReportId}`);
        if (res.ok) {
          const reportData = await res.json();
          setPolledReport(reportData);
          setPollCount((prev) => prev + 1);
        }
      } catch (err) {
        console.warn('Poll error:', err);
      }
    };

    // Initial immediate fetch
    fetchReportStatus();

    // Poll every 2 seconds
    pollIntervalRef.current = setInterval(fetchReportStatus, 2000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [submittedReportId]);

  // Reset form to submit another report
  const handleResetForm = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    setSubmittedReportId(null);
    setPolledReport(null);
    setText('');
    setUploadedMedia([]);
    setUploadError('');
    setSubmitError('');
    setPollCount(0);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-slate-950 text-slate-100 flex justify-center">
      <div className="w-full max-w-3xl space-y-6">
        {/* Header */}
        <div className="border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 font-mono text-[11px] border border-sky-500/30 font-semibold">
              CITIZEN INTAKE
            </span>
            <span className="text-xs text-slate-400">• Automated AI Ingestion &amp; Safety Routing</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
            Report Weather Observation
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Submit real-time weather incidents (rain, flooding, storm, heatwave) directly to the IMD Analytics Platform. High-impact events are safely routed for human verification.
          </p>
        </div>

        {/* Post-submission Live Tracking Card */}
        {submittedReportId ? (
          <div className="bg-slate-900 border border-sky-500/40 rounded-xl p-5 shadow-2xl shadow-sky-500/5 space-y-5 animate-in fade-in duration-300">
            {/* Header row */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-sky-400 text-lg">
                    Report #{submittedReportId}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    HTTP 202 Accepted
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Observation for <strong className="text-white">{city}, {state}</strong>
                </p>
              </div>

              {/* Status Badge */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">Current Status:</span>
                {polledReport ? (
                  <StatusBadge status={polledReport.verification_status} size="md" />
                ) : (
                  <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 animate-pulse">
                    Analyzing...
                  </span>
                )}
              </div>
            </div>

            {/* Live Progress Pipeline Stepper */}
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-medium text-slate-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                  Live Pipeline Processing
                </span>
                <span className="flex items-center gap-1.5 font-mono text-[11px] text-sky-400">
                  <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping"></span>
                  Polling every 2s (polls: {pollCount})
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Step 1 */}
                <div className="bg-slate-950 p-3 rounded-lg border border-emerald-500/30 text-xs">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-semibold mb-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>1. Intake Accepted</span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Report registered and queued into asynchronous ML task runner.
                  </p>
                </div>

                {/* Step 2 */}
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs">
                  <div className="flex items-center gap-1.5 text-sky-400 font-semibold mb-1">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>2. ML Analysis</span>
                  </div>
                  <div className="text-[11px] text-slate-300 space-y-0.5">
                    <div>Confidence: <strong className="font-mono text-white">{polledReport?.classify_conf != null ? `${Math.round(polledReport.classify_conf * 100)}%` : 'Processing...'}</strong></div>
                    <div>Fake Score: <strong className="font-mono text-white">{polledReport?.fake_score != null ? polledReport.fake_score : 'Processing...'}</strong></div>
                  </div>
                </div>

                {/* Step 3 */}
                <div className={`bg-slate-950 p-3 rounded-lg border text-xs ${
                  polledReport?.high_impact
                    ? 'border-amber-500/40 bg-amber-950/10'
                    : polledReport?.verification_status === 'verified'
                    ? 'border-emerald-500/40 bg-emerald-950/10'
                    : 'border-slate-800'
                }`}>
                  <div className="flex items-center gap-1.5 font-semibold mb-1">
                    {polledReport?.verification_status === 'verified' ? (
                      <span className="text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        3. Verified
                      </span>
                    ) : polledReport?.high_impact ? (
                      <span className="text-amber-400 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        3. Escalated to Admin
                      </span>
                    ) : (
                      <span className="text-slate-400 flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        3. Routing Verdict
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400">
                    {polledReport?.high_impact
                      ? 'High-Impact Event (Flooding/Storm) routed to Human Review Queue. Never auto-published.'
                      : polledReport?.verification_status === 'verified'
                      ? 'Report verified and broadcast live to maps and subscribers.'
                      : 'Evaluating credibility and duplicate checks...'}
                  </p>
                </div>
              </div>
            </div>

            {/* High Impact Alert notice if applicable */}
            {polledReport?.high_impact && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-300 text-xs flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-amber-400">Human-in-the-Loop Review Active</div>
                  <p className="text-[11px] text-amber-300/90 mt-0.5">
                    Because this report involves severe flooding or critical weather conditions, it is awaiting approval in the <strong>Admin Review Queue</strong>. Once approved, it will automatically appear on the Live Map.
                  </p>
                </div>
              </div>
            )}

            {/* Attached Media Evidence Preview in Tracking */}
            {((polledReport?.photos && polledReport.photos.length > 0) ||
              (polledReport?.videos && polledReport.videos.length > 0) ||
              uploadedMedia.length > 0) && (
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold flex items-center gap-1.5">
                  <ImageIcon className="w-3.5 h-3.5 text-sky-400" />
                  <span>Submitted Media Evidence</span>
                </div>
                <div className="flex flex-wrap gap-2.5 pt-1">
                  {(polledReport?.photos || uploadedMedia.filter((m) => !m.isVideo).map((m) => m.url)).map(
                    (photoUrl, pIdx) => (
                      <a
                        key={`track-photo-${pIdx}`}
                        href={photoUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="group relative block w-16 h-16 rounded-lg overflow-hidden border border-slate-700 hover:border-sky-400 transition-all bg-slate-900 shrink-0"
                        title="Click to view image in full size"
                      >
                        <img
                          src={photoUrl}
                          alt={`Report media ${pIdx + 1}`}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        />
                      </a>
                    )
                  )}

                  {(polledReport?.videos || uploadedMedia.filter((m) => m.isVideo).map((m) => m.url)).map(
                    (videoUrl, vIdx) => (
                      <div
                        key={`track-video-${vIdx}`}
                        className="w-36 rounded-lg overflow-hidden border border-slate-700 bg-black flex flex-col justify-center shrink-0"
                      >
                        <video src={videoUrl} controls preload="metadata" className="w-full max-h-20 object-cover" />
                      </div>
                    )
                  )}
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <button
                type="button"
                onClick={handleResetForm}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-2 cursor-pointer transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Submit Another Report</span>
              </button>

              <button
                type="button"
                onClick={() => onSwitchTab('dashboard')}
                className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold flex items-center gap-2 cursor-pointer transition-colors shadow-lg shadow-sky-600/20"
              >
                <span>View on Live Map</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ) : (
          /* Submission Form */
          <form onSubmit={handleSubmit} className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 sm:p-6 space-y-6 shadow-xl">
            {submitError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{submitError}</span>
              </div>
            )}

            {/* 1. Event Category Chips */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2.5">
                Select Weather Event Category <span className="text-rose-400">*</span>
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {EVENT_CATEGORIES.map((cat) => {
                  const Icon = EVENT_ICON_MAP[cat.value] || CloudRain;
                  const isSelected = category === cat.value;
                  return (
                    <button
                      key={cat.value}
                      type="button"
                      onClick={() => setCategory(cat.value)}
                      className={`p-2.5 rounded-lg border text-left flex items-center gap-2 transition-all cursor-pointer ${
                        isSelected
                          ? 'border-sky-500 bg-sky-500/15 text-white ring-1 ring-sky-500 shadow-md shadow-sky-500/10'
                          : 'border-slate-800 bg-slate-950/70 text-slate-300 hover:bg-slate-800/60 hover:border-slate-700'
                      }`}
                    >
                      <div
                        className="w-7 h-7 rounded-md flex items-center justify-center shrink-0"
                        style={{
                          backgroundColor: `${cat.color}25`,
                          color: cat.color,
                        }}
                      >
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="truncate">
                        <div className="font-semibold text-xs truncate">{cat.label}</div>
                        {cat.value === 'flooding' && (
                          <span className="text-[10px] text-rose-400 font-mono">High Impact</span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 2. City and State with Quick Presets */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-slate-300">
                  Location (City &amp; State) <span className="text-rose-400">*</span>
                </label>
                <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                  <span>Quick demo presets:</span>
                  <button
                    type="button"
                    onClick={() => handleApplyPreset('Mumbai', 'Maharashtra', 19.076, 72.877, 'flooding', 'Severe waterlogging near Kurla station and Hindmata, water above 2.5 feet.')}
                    className="text-sky-400 hover:underline cursor-pointer"
                  >
                    Mumbai
                  </button>
                  <span>•</span>
                  <button
                    type="button"
                    onClick={() => handleApplyPreset('Patna', 'Bihar', 25.594, 85.137, 'flooding', 'गांधी मैदान और राजेंद्र नगर में बाढ़ का पानी भर गया है, सड़कें पूरी तरह जलमग्न हैं।')}
                    className="text-sky-400 hover:underline cursor-pointer"
                  >
                    Patna (Hindi)
                  </button>
                  <span>•</span>
                  <button
                    type="button"
                    onClick={() => handleApplyPreset('Chennai', 'Tamil Nadu', 13.082, 80.27, 'flooding', 'Heavy inundation in Velachery, rescue boats deployed.')}
                    className="text-sky-400 hover:underline cursor-pointer"
                  >
                    Chennai
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <input
                    type="text"
                    required
                    placeholder="Enter city (e.g. Mumbai, Patna)"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
                  />
                </div>
                <div>
                  <input
                    type="text"
                    required
                    placeholder="Enter state (e.g. Maharashtra, Bihar)"
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors"
                  />
                </div>
              </div>
            </div>

            {/* 3. Browser GPS Capture with Retry */}
            <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Compass className="w-4 h-4 text-sky-400" />
                  <span className="text-xs font-semibold text-slate-300">
                    GPS Coordinates
                  </span>
                  {gpsStatus === 'success' && (
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-mono border border-emerald-500/30 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" /> Captured
                    </span>
                  )}
                </div>

                {/* GPS Capture / Retry Button */}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleCaptureGps}
                    disabled={gpsStatus === 'locating'}
                    className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
                      gpsStatus === 'error'
                        ? 'bg-amber-600 hover:bg-amber-500 text-white'
                        : 'bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700'
                    }`}
                  >
                    {gpsStatus === 'locating' ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Acquiring GPS...</span>
                      </>
                    ) : gpsStatus === 'error' ? (
                      <>
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Retry GPS Capture</span>
                      </>
                    ) : (
                      <>
                        <Compass className="w-3.5 h-3.5" />
                        <span>{gpsStatus === 'success' ? 'Update Location' : 'Capture Current GPS'}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {gpsError && (
                <div className="text-[11px] text-amber-400 bg-amber-950/20 border border-amber-900/40 p-2 rounded flex items-center justify-between gap-2">
                  <span>{gpsError}</span>
                  <button
                    type="button"
                    onClick={handleCaptureGps}
                    className="underline text-amber-300 font-semibold cursor-pointer shrink-0"
                  >
                    Retry
                  </button>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="block text-[11px] text-slate-400 mb-0.5">Latitude</label>
                  <input
                    type="number"
                    step="any"
                    placeholder="e.g. 19.0760"
                    value={lat}
                    onChange={(e) => setLat(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-600 font-mono focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-slate-400 mb-0.5">Longitude</label>
                  <input
                    type="number"
                    step="any"
                    placeholder="e.g. 72.8770"
                    value={lon}
                    onChange={(e) => setLon(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-600 font-mono focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>
            </div>

            {/* 4. Text Area (Bilingual English / Hindi) */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-300">
                  Observation Description (English / हिन्दी)
                </label>
                <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                  <span>Quick text samples:</span>
                  <button
                    type="button"
                    onClick={() => setText('Flash flooding on highway, water level above 3 feet, multiple vehicles trapped in underpass, rescue teams needed immediately.')}
                    className="text-sky-400 hover:underline cursor-pointer"
                  >
                    Flood Alert (EN)
                  </button>
                  <span>•</span>
                  <button
                    type="button"
                    onClick={() => setText('इलाके में भीषण जलभराव और बाढ़, घरों में पानी घुस रहा है, रास्ते पूरी तरह बंद हैं।')}
                    className="text-sky-400 hover:underline cursor-pointer"
                  >
                    बाढ़ विवरण (HI)
                  </button>
                </div>
              </div>

              <textarea
                rows={3}
                placeholder="Describe current ground conditions in English or Hindi (e.g., water level, stranded traffic, rainfall intensity, casualties, dam overflow)..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 transition-colors leading-relaxed"
              />
            </div>

            {/* 5. Photo & Video Upload */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-slate-300">
                  Attach Photo / Video Evidence (Optional)
                </label>
                <span className="text-[11px] text-slate-400">
                  Max 10 MB per file • Images &amp; Videos only
                </span>
              </div>

              {/* Upload Dropzone / Button */}
              <div
                onClick={() => fileInputRef.current && fileInputRef.current.click()}
                className="border-2 border-dashed border-slate-800 hover:border-sky-500/60 bg-slate-950/60 hover:bg-slate-900/50 rounded-xl p-4 sm:p-5 text-center cursor-pointer transition-all group"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/*,video/*"
                  onChange={handleFileChange}
                  className="hidden"
                />
                <div className="flex flex-col items-center justify-center gap-2">
                  <div className="w-10 h-10 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center group-hover:scale-110 transition-transform">
                    {uploadingMedia ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <UploadCloud className="w-5 h-5" />
                    )}
                  </div>
                  <div>
                    <span className="text-xs font-semibold text-slate-200 group-hover:text-sky-300 transition-colors">
                      {uploadingMedia ? 'Uploading media to storage...' : 'Click to select or drag photo/video'}
                    </span>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      JPEG, PNG, WebP, GIF, MP4, WebM, MOV (Stored in MinIO with local fallback)
                    </p>
                  </div>
                </div>
              </div>

              {/* Upload Error Banner */}
              {uploadError && (
                <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                    <span>{uploadError}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setUploadError('')}
                    className="text-slate-400 hover:text-white"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}

              {/* Uploaded Thumbnails Preview Gallery */}
              {uploadedMedia.length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-1">
                  {uploadedMedia.map((media, idx) => (
                    <div
                      key={media.url || idx}
                      className="bg-slate-950 border border-slate-800 rounded-lg p-2 relative group flex flex-col gap-1.5"
                    >
                      <div className="w-full h-24 rounded overflow-hidden bg-slate-900 border border-slate-800/80 flex items-center justify-center relative">
                        {media.isVideo ? (
                          <video
                            src={media.url}
                            className="w-full h-full object-cover"
                            muted
                          />
                        ) : (
                          <img
                            src={media.url}
                            alt={media.filename}
                            className="w-full h-full object-cover"
                          />
                        )}
                        <span className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-slate-950/80 text-[9px] font-mono text-slate-300 border border-slate-700">
                          {media.isVideo ? 'VIDEO' : 'PHOTO'}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-400">
                        <span className="truncate max-w-[120px]" title={media.filename}>
                          {media.filename}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRemoveMedia(idx)}
                          className="text-slate-500 hover:text-rose-400 p-0.5 rounded transition-colors"
                          title="Remove file"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                        <span>{(media.size_bytes / 1024).toFixed(0)} KB</span>
                        <span className="text-emerald-400 flex items-center gap-0.5">
                          <CheckCircle2 className="w-2.5 h-2.5" /> Ready
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Submit Button */}
            <div className="pt-2 flex items-center justify-between gap-4">
              <span className="text-[11px] text-slate-400">
                Submissions automatically trigger multilingual NLP &amp; deduplication screening.
              </span>

              <button
                type="submit"
                disabled={submitting}
                className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white font-semibold text-xs flex items-center gap-2 cursor-pointer transition-all shadow-lg shadow-sky-600/20 disabled:opacity-50 shrink-0"
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Submitting...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Submit Weather Report</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
