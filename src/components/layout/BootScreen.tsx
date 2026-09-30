import React, { useEffect, useState } from 'react';
import { BrandLogo } from '../ui/BrandLogo';
import { useTheme } from '../../hooks/use-theme';

export interface BootScreenProps {
  onComplete: () => void;
}

export const BootScreen: React.FC<BootScreenProps> = ({ onComplete }) => {
  const { resolvedTheme } = useTheme();
  const [bootStep, setBootStep] = useState(0);

  useEffect(() => {
    // Respect prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      onComplete();
      return;
    }

    const t1 = setTimeout(() => setBootStep(1), 400);
    const t2 = setTimeout(() => setBootStep(2), 1000);
    const t3 = setTimeout(() => onComplete(), 1600);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [onComplete]);

  return (
    <div
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center transition-opacity duration-500 font-mono select-none ${
        resolvedTheme === 'light' ? 'bg-slate-50 text-slate-900' : 'bg-[#090D11] text-slate-100'
      }`}
    >
      <div className="flex flex-col items-center space-y-4 max-w-xs text-center px-4">
        {/* Subtle Logo Reveal */}
        <div className={`transition-all duration-700 ${bootStep >= 0 ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}>
          <BrandLogo variant="logo" className="h-10" />
        </div>

        {/* Small Status & Initialization Indicators */}
        <div className="h-12 flex flex-col items-center justify-center space-y-1">
          {bootStep >= 1 && (
            <div className="flex items-center gap-2 text-xs text-cyan-500 animate-in fade-in duration-300">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span>Initialising Local AI Runtime...</span>
            </div>
          )}
          {bootStep >= 2 && (
            <div className="text-[10px] text-slate-500 animate-in fade-in duration-300">
              EnvironmentReady (v0.4.2)
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
