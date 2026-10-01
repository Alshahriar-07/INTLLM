import React from 'react';
import { cn } from '../../lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** DEPRECATED: retained for API compat, no longer renders any glow effect. */
  glow?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, glow: _glow = false, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('bg-surface border border-border rounded-lg p-4 transition-colors duration-150', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);
Card.displayName = 'Card';
