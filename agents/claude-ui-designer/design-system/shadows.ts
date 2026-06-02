// Design System - Shadows
// 基于 Apple Design Language

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  base: '0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)',
  md: '0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px rgba(0, 0, 0, 0.1), 0 10px 10px rgba(0, 0, 0, 0.04)',
  '2xl': '0 25px 50px rgba(0, 0, 0, 0.25)',
  inner: 'inset 0 2px 4px rgba(0, 0, 0, 0.06)',
} as const;

export type Shadows = typeof shadows;

// 交互状态阴影
export const interactiveShadows = {
  // 按钮
  button: {
    default: '0 1px 3px rgba(0, 0, 0, 0.1)',
    hover: '0 4px 12px rgba(0, 0, 0, 0.15)',
    active: '0 1px 2px rgba(0, 0, 0, 0.1)',
  },
  // 卡片
  card: {
    default: '0 1px 3px rgba(0, 0, 0, 0.08)',
    hover: '0 12px 40px rgba(0, 0, 0, 0.12)',
    active: '0 4px 12px rgba(0, 0, 0, 0.1)',
  },
  // 输入框
  input: {
    default: 'inset 0 1px 2px rgba(0, 0, 0, 0.06)',
    focus: '0 0 0 3px rgba(0, 122, 255, 0.2)',
  },
  // 模态框
  modal: '0 25px 50px rgba(0, 0, 0, 0.25)',
} as const;

export default shadows;
