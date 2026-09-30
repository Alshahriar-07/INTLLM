import React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-500 disabled:pointer-events-none disabled:opacity-50 select-none rounded-md';
    
    const variants = {
      primary: 'bg-cyan-600 text-white hover:bg-cyan-500 shadow-sm border border-cyan-500/30 active:bg-cyan-700',
      secondary: 'bg-[#1E293B] text-slate-200 hover:bg-[#2C3B53] border border-slate-700/60 active:bg-[#15202E]',
      outline: 'border border-slate-700 bg-transparent text-slate-300 hover:bg-slate-800/60 hover:text-white',
      ghost: 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200',
      danger: 'bg-rose-900/40 text-rose-300 border border-rose-700/50 hover:bg-rose-900/70 hover:text-white'
    };

    const sizes = {
      sm: 'h-8 px-3 text-xs gap-1.5',
      md: 'h-9 px-4 text-sm gap-2',
      lg: 'h-11 px-6 text-base gap-2.5',
      icon: 'h-8 w-8 p-0'
    };

    return (
      <button
        ref={ref}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
