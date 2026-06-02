// Design System - Colors
// 基于 Apple Design Language

export const colors = {
  primary: {
    blue: '#007AFF',
    purple: '#5856D6',
    pink: '#FF2D55',
  },
  semantic: {
    success: '#34C759',
    warning: '#FF9500',
    error: '#FF3B30',
    info: '#5AC8FA',
  },
  neutral: {
    black: '#1D1D1F',
    dark: '#272730',
    gray: '#86868B',
    lightGray: '#D2D2D7',
    ultraLight: '#F5F5F7',
    white: '#FFFFFF',
  },
  dark: {
    background: ['#000000', '#1D1D1F', '#2C2C2E'],
    surface: ['#3A3A3C', '#48484A'],
    text: ['#FFFFFF', 'rgba(235, 235, 245, 0.9)', 'rgba(235, 235, 245, 0.6)'],
  },
} as const;

export type Colors = typeof colors;

// TailwindCSS 颜色配置
export const tailwindColors = {
  // Primary
  'apple-blue': '#007AFF',
  'apple-purple': '#5856D6',
  'apple-pink': '#FF2D55',
  // Semantic
  'apple-success': '#34C759',
  'apple-warning': '#FF9500',
  'apple-error': '#FF3B30',
  'apple-info': '#5AC8FA',
  // Neutral
  'apple-black': '#1D1D1F',
  'apple-dark': '#272730',
  'apple-gray': '#86868B',
  'apple-light-gray': '#D2D2D7',
  'apple-ultra-light': '#F5F5F7',
  'apple-white': '#FFFFFF',
};

export default colors;
