import React from 'react';
import { STATUS_CONFIG } from '../constants';
import { CheckCircle2, Clock, AlertOctagon, HelpCircle } from 'lucide-react';

const ICONS = {
  verified: CheckCircle2,
  under_review: Clock,
  rejected: AlertOctagon,
  unverified: HelpCircle,
};

export function StatusBadge({ status, size = 'sm' }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.unverified;
  const IconComponent = ICONS[status] || HelpCircle;

  const sizeClasses = size === 'xs'
    ? 'px-2 py-0.5 text-[11px] gap-1'
    : 'px-2.5 py-1 text-xs gap-1.5';

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full uppercase tracking-wider backdrop-blur-sm ${sizeClasses} ${cfg.badgeClass}`}
    >
      <IconComponent className={size === 'xs' ? 'w-3 h-3' : 'w-3.5 h-3.5'} />
      {cfg.label}
    </span>
  );
}
