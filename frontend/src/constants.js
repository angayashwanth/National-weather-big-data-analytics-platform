export const EVENT_CATEGORIES = [
  { value: 'rainfall', label: 'Rainfall', icon: 'CloudRain', color: '#38bdf8' },
  { value: 'thunderstorm', label: 'Thunderstorm', icon: 'CloudLightning', color: '#c084fc' },
  { value: 'flooding', label: 'Flooding', icon: 'Waves', color: '#06b6d4' },
  { value: 'heatwave', label: 'Heatwave', icon: 'Flame', color: '#fb923c' },
  { value: 'fog', label: 'Dense Fog', icon: 'CloudFog', color: '#94a3b8' },
  { value: 'dust_storm', label: 'Dust Storm', icon: 'Wind', color: '#f59e0b' },
  { value: 'strong_wind', label: 'Strong Wind', icon: 'Compass', color: '#2dd4bf' },
];

export const STATUS_CONFIG = {
  verified: {
    label: 'Verified',
    color: '#22c55e',
    badgeClass: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
    dotClass: 'bg-emerald-400',
  },
  under_review: {
    label: 'Under Review',
    color: '#f59e0b',
    badgeClass: 'bg-amber-500/15 text-amber-400 border border-amber-500/30',
    dotClass: 'bg-amber-400',
  },
  rejected: {
    label: 'Rejected',
    color: '#ef4444',
    badgeClass: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
    dotClass: 'bg-rose-400',
  },
  unverified: {
    label: 'Unverified',
    color: '#9ca3af',
    badgeClass: 'bg-slate-500/15 text-slate-400 border border-slate-500/30',
    dotClass: 'bg-slate-400',
  },
};

export const SOURCE_TYPE_LABELS = {
  citizen_report: 'Citizen Report',
  social_media: 'Social Media',
  website: 'News / Website',
  api: 'Official API',
  public_dataset: 'Public Dataset',
};

export const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Delhi', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh',
  'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra',
  'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha',
  'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana',
  'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
];

export const MAP_CENTER_INDIA = [78.9629, 20.5937];
export const MAP_DEFAULT_ZOOM = 4.6;
