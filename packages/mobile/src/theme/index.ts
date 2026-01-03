/**
 * JARVIS Mobile App Theme
 * Inspired by Iron Man's JARVIS interface - dark, sophisticated, with accent colors.
 */

export const colors = {
  // Primary palette - JARVIS blue
  primary: '#00A8FF',
  primaryDark: '#0077B5',
  primaryLight: '#5CC9FF',

  // Secondary - Arc reactor glow
  secondary: '#00E5FF',
  secondaryDark: '#00B8D4',
  secondaryLight: '#6EFFFF',

  // Accent - Warning/Alert
  accent: '#FFD700',
  accentDark: '#FFA000',
  accentLight: '#FFE54C',

  // Status colors
  success: '#00E676',
  warning: '#FFAB00',
  error: '#FF5252',
  info: '#448AFF',

  // Background hierarchy (darkest to lightest)
  background: '#0A0E14',
  backgroundSecondary: '#0F1419',
  backgroundTertiary: '#151B23',
  surface: '#1A222D',
  surfaceElevated: '#232D3B',

  // Text hierarchy
  textPrimary: '#FFFFFF',
  textSecondary: '#B0BEC5',
  textTertiary: '#607D8B',
  textDisabled: '#37474F',

  // Borders
  border: '#263238',
  borderLight: '#37474F',
  borderFocus: '#00A8FF',

  // Overlays
  overlay: 'rgba(0, 0, 0, 0.7)',
  overlayLight: 'rgba(0, 0, 0, 0.5)',

  // Special JARVIS effects
  glow: 'rgba(0, 168, 255, 0.3)',
  glowIntense: 'rgba(0, 168, 255, 0.6)',
  hologram: 'rgba(0, 229, 255, 0.1)',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const borderRadius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  round: 9999,
};

export const typography = {
  // Font families
  fontFamily: {
    regular: 'System',
    medium: 'System',
    bold: 'System',
    mono: 'Menlo',
  },

  // Font sizes
  fontSize: {
    xs: 10,
    sm: 12,
    md: 14,
    lg: 16,
    xl: 18,
    xxl: 24,
    xxxl: 32,
    display: 48,
  },

  // Line heights
  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },

  // Font weights
  fontWeight: {
    regular: '400' as const,
    medium: '500' as const,
    semibold: '600' as const,
    bold: '700' as const,
  },
};

export const shadows = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 2,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 4,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  glow: {
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 10,
    elevation: 10,
  },
};

export const animations = {
  duration: {
    fast: 150,
    normal: 300,
    slow: 500,
  },
  easing: {
    easeIn: 'ease-in',
    easeOut: 'ease-out',
    easeInOut: 'ease-in-out',
  },
};

// React Navigation theme
export const navigationTheme = {
  dark: true,
  colors: {
    primary: colors.primary,
    background: colors.background,
    card: colors.surface,
    text: colors.textPrimary,
    border: colors.border,
    notification: colors.accent,
  },
};

// Combined theme object
export const theme = {
  colors,
  spacing,
  borderRadius,
  typography,
  shadows,
  animations,
  navigationTheme,
};

export type Theme = typeof theme;
export type Colors = typeof colors;
export type Spacing = typeof spacing;

export default theme;
