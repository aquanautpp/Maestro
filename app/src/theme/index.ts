// Design tokens - calm, positive colors
export const colors = {
  // Primary - calming green
  primary: '#4CAF50',
  primaryLight: '#81C784',
  primaryDark: '#388E3C',

  // Secondary - soft blue
  secondary: '#64B5F6',
  secondaryLight: '#90CAF9',
  secondaryDark: '#42A5F5',

  // Backgrounds
  background: '#F5F9F5',
  surface: '#FFFFFF',
  surfaceElevated: '#FFFFFF',

  // Text
  textPrimary: '#2E3D2E',
  textSecondary: '#5C6B5C',
  textMuted: '#8A998A',
  textOnPrimary: '#FFFFFF',

  // Status
  success: '#66BB6A',
  warning: '#FFB74D',
  error: '#EF5350',

  // Misc
  border: '#E0E8E0',
  divider: '#E8F0E8',
  disabled: '#B8C8B8',

  // Chart colors
  chartLine: '#4CAF50',
  chartFill: 'rgba(76, 175, 80, 0.2)',
  chartGrid: '#E0E8E0',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const fontSizes = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 20,
  xl: 24,
  xxl: 32,
  hero: 48,
};

export const fontWeights = {
  regular: '400' as const,
  medium: '500' as const,
  semibold: '600' as const,
  bold: '700' as const,
};

export const borderRadius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 9999,
};

export const shadows = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 4,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 8,
  },
};

export const theme = {
  colors,
  spacing,
  fontSizes,
  fontWeights,
  borderRadius,
  shadows,
};

export type Theme = typeof theme;
