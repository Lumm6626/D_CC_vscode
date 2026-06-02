// Design System - Typography
// 基于 Apple Design Language

export const typography = {
  fontFamily: {
    display: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif",
    text: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', sans-serif",
    mono: "'SF Mono', 'Fira Code', 'Consolas', monospace",
  },
  fontSize: {
    xs: '12px',
    sm: '14px',
    base: '16px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '30px',
    '4xl': '36px',
    '5xl': '48px',
  },
  fontWeight: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },
} as const;

export type Typography = typeof typography;

// TailwindCSS 字体配置
export const tailwindTypography = {
  fontFamily: {
    'sf-display': "-apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif",
    'sf-text': "-apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
    'sf-mono': "'SF Mono', 'Fira Code', 'Consolas', monospace",
  },
  fontSize: {
    'xs': '12px',
    'sm': '14px',
    'base': '16px',
    'lg': '18px',
    'xl': '20px',
    '2xl': '24px',
    '3xl': '30px',
    '4xl': '36px',
    '5xl': '48px',
  },
};

export default typography;
