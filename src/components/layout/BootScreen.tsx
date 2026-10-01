import React, { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { BrandLogo } from '../ui/BrandLogo';

export interface BootScreenProps {
  onComplete: () => void;
}

export const BootScreen: React.FC<BootScreenProps> = ({ onComplete }) => {
  const [showStatus, setShowStatus] = useState(false);

  useEffect(() => {
    // Respect prefers-reduced-motion: skip the animation entirely.
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      onComplete();
      return;
    }

    const t1 = setTimeout(() => setShowStatus(true), 500);
    const t2 = setTimeout(() => onComplete(), 1300);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [onComplete]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-canvas text-primary animate-fade-in">
      <div className="flex flex-col items-center gap-5 max-w-xs text-center px-4">
        <BrandLogo variant="logo" className="h-10" />
        <div className="h-6 flex items-center">
          {showStatus && (
            <div className="flex items-center gap-2 text-xs text-muted font-mono animate-fade-in">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" aria-hidden />
              <span>Initialising local AI runtime…</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
