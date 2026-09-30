import React from 'react';
import { cn } from '../../lib/utils';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'cyan' | 'emerald' | 'amber' | 'rose' | 'outline';
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = 'default',
  size = 'md',
  children,
  ...props
}) => {
  const baseStyles = 'inline-flex items-center font-mono font-medium rounded border transition-colors select-none';
  
  const variants = {
    default: 'bg-slate-800/80 text-slate-300 border-slate-700/60',
    cyan: 'bg-cyan-950/60 text-cyan-400 border-cyan-700/50',
    emerald: 'bg-emerald-950/60 text-emerald-400 border-emerald-700/50',
    amber: 'bg-amber-950/60 text-amber-400 border-amber-700/50',
    rose: 'bg-rose-950/60 text-rose-400 border-rose-700/50',
    outline: 'bg-transparent text-slate-400 border-slate-700'
  };

  const sizes = {
    sm: 'px-1.5 py-0.5 text-[10px] gap-1',
    md: 'px-2 py-0.5 text-xs gap-1.5'
  };

  return (
    <span className={cn(baseStyles, variants[variant], sizes[size], className)} {...props}>
      {children}
    </span>
  );
};
