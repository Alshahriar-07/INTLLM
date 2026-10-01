import React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg' | 'icon' | 'icon-sm';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', children, ...props }, ref) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium transition-colors duration-150 select-none rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-1 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50';

    const variants = {
      primary:
        'bg-accent text-accent-foreground hover:bg-accent-hover active:bg-accent-hover shadow-sm',
      secondary: 'bg-elevated text-primary border border-border hover:bg-panel-hover',
      outline: 'border border-border bg-transparent text-secondary hover:bg-panel-hover hover:text-primary',
      ghost: 'text-muted hover:bg-panel-hover hover:text-primary',
      danger: 'bg-error/10 text-error border border-error/30 hover:bg-error/20'
    };

    const sizes = {
      sm: 'h-7 px-2.5 text-xs gap-1.5',
      md: 'h-8 px-3 text-sm gap-1.5',
      lg: 'h-10 px-4 text-sm gap-2',
      icon: 'h-8 w-8 p-0',
      'icon-sm': 'h-6 w-6 p-0'
    };

    return (
      <button ref={ref} className={cn(baseStyles, variants[variant], sizes[size], className)} {...props}>
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
