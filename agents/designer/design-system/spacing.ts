// Design System - Spacing
// 基于 8px 网格系统

export const spacing = {
  '0': '0px',
  'px': '1px',
  '0.5': '2px',
  '1': '4px',
  '2': '8px',
  '3': '12px',
  '4': '16px',
  '5': '20px',
  '6': '24px',
  '8': '32px',
  '10': '40px',
  '12': '48px',
  '16': '64px',
  '20': '80px',
  '24': '96px',
} as const;

export type Spacing = typeof spacing;

// TailwindCSS 间距配置（扩展标准间距以包含设计系统值）
export const tailwindSpacing = {
  '0': '0px',
  'px': '1px',
  '0.5': '2px',
  '1': '4px',
  '2': '8px',
  '3': '12px',
  '4': '16px',
  '5': '20px',
  '6': '24px',
  '8': '32px',
  '10': '40px',
  '12': '48px',
  '16': '64px',
  '20': '80px',
  '24': '96px',
};

export default spacing;
