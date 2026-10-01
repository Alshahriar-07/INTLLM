import React from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'cyan' | 'emerald' | 'amber' | 'rose' | 'purple' | 'outline';
  size?: 'sm' | 'md';
  /** Subtle "status dot" style used by system indicators. */
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  size = 'md',
  dot = false,
  children,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center font-mono font-medium rounded border transition-colors select-none whitespace-nowrap';

  const variants = {
    default: 'bg-panel-hover text-secondary border-border',
    cyan: 'bg-accent/10 text-accent border-accent/25',
    emerald: 'bg-success/10 text-success border-success/25',
    amber: 'bg-warning/10 text-warning border-warning/25',
    rose: 'bg-error/10 text-error border-error/25',
    purple: 'bg-accent/10 text-accent border-accent/25',
    outline: 'bg-transparent text-muted border-border'
  };

  const sizes = {
    sm: 'px-1.5 py-0.5 text-[10px] gap-1',
    md: 'px-2 py-0.5 text-xs gap-1.5'
  };

  return (
    <span className={cn(baseStyles, variants[variant], sizes[size], className)} {...props}>
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80" aria-hidden />}
      {children}
    </span>
  );
};
