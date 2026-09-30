import React from 'react';
import { useTheme } from '../../hooks/use-theme';
import logoOnDark from '../../assets/brand/INTLLM-logo-on-dark.png';
import logoOnWhite from '../../assets/brand/INTLLM-logo-on-white.png';
import appIcon from '../../assets/brand/INTLLM-app-icon.png';
import icon128 from '../../assets/brand/INTLLM-icon-128.png';

export interface BrandLogoProps {
  variant?: 'icon' | 'logo' | 'full';
  className?: string;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({ variant = 'logo', className = 'h-7' }) => {
  const { resolvedTheme } = useTheme();

  if (variant === 'icon') {
    return (
      <img
        src={appIcon || icon128}
        alt="INTLLM Icon"
        className={`object-contain select-none ${className}`}
      />
    );
  }

  const logoSrc = resolvedTheme === 'light' ? logoOnWhite : logoOnDark;

  return (
    <img
      src={logoSrc}
      alt="INTLLM"
      className={`object-contain select-none ${className}`}
    />
  );
};
