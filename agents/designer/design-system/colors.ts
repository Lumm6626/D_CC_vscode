// Design System - Colors
// 基于 Apple 官方来源数据
// 来源：
//   - 品牌色 (#000000, #FFFFFF, #555555, #A6A6A6): Apple 品牌标识指南 PDF
//   - 官网用色 (#F5F5F7, #1D1D1F, #0066CC): Mobbin Apple Colors (CSS 实际值)
//   - 系统色 (#007AFF, #34C759, #FF3B30 等): Apple HIG Color
// 交叉验证文件: source-references.md

export const colors = {
  // ---- Apple 官方品牌色 (Brand Colors) ----
  brand: {
    appleBlue: '#0066CC',       // Apple 官网品牌蓝（导航栏启用色、链接色）
    appleBlueLight: '#007AFF',  // iOS/macOS 系统蓝（主操作按钮）
    appleBlack: '#000000',      // Apple 品牌纯黑
    appleWhite: '#FFFFFF',      // Apple 品牌纯白
    spaceGray: '#555555',       // Apple 深空灰（产品页辅助色）
    silver: '#A6A6A6',          // Apple 银色（二级图标、辅助文案）
  },

  // ---- 系统语义色 (iOS/macOS System Colors) ----
  system: {
    blue: '#007AFF',            // 主操作、链接、Highlight
    purple: '#5856D6',          // 次要强调、特殊功能
    pink: '#FF2D55',            // 社交、心形、热情
    red: '#FF3B30',             // 错误、删除、危险操作
    orange: '#FF9500',          // 警告、注意提示
    yellow: '#FFCC00',          // 提醒、标记
    green: '#34C759',           // 成功、确认、正向
    teal: '#5AC8FA',            // 信息、提示
    indigo: '#5856D6',          // 辅助色（visionOS 常用）
    mint: '#00C7BE',            // 清新色（watchOS 健康环用色）
    cyan: '#32ADE6',            // 信息补充色
  },

  // ---- Apple 官网中性色 (基于 apple.com 实际 CSS) ----
  neutral: {
    textPrimary: '#1D1D1F',     // Apple 官网正文黑（#1D1D1F = 最常用文字色）
    textSecondary: '#6E6E73',   // Apple 官网次要文字（副标题、描述）
    textTertiary: '#86868B',    // Apple 官网三级文字（脚注、说明）
    border: '#D2D2D7',          // Apple 官网分割线、边框色
    borderLight: '#E8E8ED',     // 更浅的分割线
    background: '#F5F5F7',      // Apple 官网页面背景（极淡灰）
    backgroundElevated: '#FFFFFF', // 卡片、容器背景（纯白）
    backgroundDark: '#1D1D1F',  // Apple 深色区域背景（产品页深色模块）
    backgroundDarkElevated: '#2D2D2F', // 深色卡片背景
    white: '#FFFFFF',
    black: '#000000',
  },

  // ---- 深色模式 (Dark Mode) ----
  dark: {
    background: '#000000',           // 系统深色背景
    backgroundElevated: '#1C1C1E',   // 深色卡片
    surface: '#2C2C2E',              // 深色表面
    surfaceElevated: '#3A3A3C',      // 深色浮层
    separator: '#38383A',            // 深色分割线
    textPrimary: '#FFFFFF',
    textSecondary: 'rgba(235, 235, 245, 0.85)',
    textTertiary: 'rgba(235, 235, 245, 0.55)',
    fill: 'rgba(120, 120, 128, 0.36)',
    link: '#0A84FF',                 // 深色模式链接蓝
  },

  // ---- Apple 官网产品页专色（针对具体产品渲染） ----
  product: {
    // iPhone / iPad / Mac 产品页常见渐变和强调色
    gradientBlue: '#0071E3',   // 产品页渐变主蓝
    gradientPurple: '#AF52DE', // iPhone 渐变紫
    gradientOrange: '#FF9F0A', // 暖色调强调
    gradientRed: '#FF453A',    // 产品页红色强调
    heroDark: '#1D1D1F',      // 产品 Hero 深色背景
    heroLight: '#F5F5F7',     // 产品 Hero 浅色背景
  },
} as const;

export type Colors = typeof colors;

// ---- TailwindCSS 扩展配置 ----
export const tailwindColors = {
  // Apple 品牌色
  'apple-blue': '#0066CC',
  'apple-blue-light': '#007AFF',
  'apple-space-gray': '#555555',
  'apple-silver': '#A6A6A6',
  // 语义色
  'apple-system-blue': '#007AFF',
  'apple-system-purple': '#5856D6',
  'apple-system-pink': '#FF2D55',
  'apple-system-red': '#FF3B30',
  'apple-system-orange': '#FF9500',
  'apple-system-green': '#34C759',
  'apple-system-teal': '#5AC8FA',
  // 中性色
  'apple-text': '#1D1D1F',
  'apple-text-secondary': '#6E6E73',
  'apple-text-tertiary': '#86868B',
  'apple-border': '#D2D2D7',
  'apple-border-light': '#E8E8ED',
  'apple-bg': '#F5F5F7',
  'apple-white': '#FFFFFF',
  'apple-black': '#000000',
};

export default colors;
