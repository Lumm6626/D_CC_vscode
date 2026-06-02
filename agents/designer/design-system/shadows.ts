// Design System - Shadows & Effects
// 基于 Apple 官网 (apple.com / apple.com.cn) + Apple HIG + Liquid Glass (WWDC25)
//
// Apple 阴影设计原则：
// 1. 自然光感 - 模拟真实光照，阴影柔和、不突兀
// 2. 层次递进 - 阴影深度映射 UI 层级（卡片 < 浮层 < 模态框）
// 3. Apple 官网卡片阴影非常克制，hover 时极其微妙（深度 ≈2-4px）
// 4. 2025 年 WWDC25 引入 Liquid Glass 新设计语言，材质呈现动态玻璃质感
// 5. 色调偏移：Apple 阴影略偏蓝（中性灰带微蓝调），模拟真实环境光

export const shadows = {
  // ---- 基础阴影层级 (Elevation) ----
  /** 极小阴影 - 轻微悬浮 */
  sm: '0 1px 2px rgba(0, 0, 0, 0.06), 0 1px 1px rgba(0, 0, 0, 0.03)',
  /** 基础阴影 - 默认卡片、按钮 */
  base: '0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04)',
  /** 中等阴影 - 悬停/选中状态 */
  md: '0 4px 8px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)',
  /** 大阴影 - 浮层、Dropdown */
  lg: '0 10px 20px rgba(0, 0, 0, 0.08), 0 4px 8px rgba(0, 0, 0, 0.04)',
  /** 特大阴影 - 模态框、弹窗 */
  xl: '0 20px 30px rgba(0, 0, 0, 0.10), 0 8px 16px rgba(0, 0, 0, 0.06)',
  /** 最大阴影 - 全屏模态、顶部组件 */
  '2xl': '0 25px 50px rgba(0, 0, 0, 0.15), 0 10px 20px rgba(0, 0, 0, 0.08)',
  /** 内阴影 - 输入框 */
  inner: 'inset 0 1px 2px rgba(0, 0, 0, 0.05)',
  /** 内阴影强调 - 输入框 focus */
  innerFocus: 'inset 0 1px 2px rgba(0, 0, 0, 0.05), 0 0 0 3px rgba(0, 122, 255, 0.2)',
  /** 内阴影错误 */
  innerError: 'inset 0 1px 2px rgba(0, 0, 0, 0.05), 0 0 0 3px rgba(255, 59, 48, 0.2)',

  // ---- 交互状态阴影 (Apple 官网风格 - 极其克制) ----
  interactive: {
    // 按钮
    button: {
      default: '0 1px 2px rgba(0, 0, 0, 0.08)',
      hover: '0 4px 12px rgba(0, 122, 255, 0.20)',  // 蓝色辉光 hover
      active: '0 1px 2px rgba(0, 0, 0, 0.06)',
      disabled: 'none',
    },
    // 卡片 hover（Apple 官网卡片 hover 极度克制，极写实）
    card: {
      default: '0 1px 2px rgba(0, 0, 0, 0.05)',
      hover: '0 4px 12px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.03)',
      hoverElevated: '0 12px 40px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.04)',
      active: '0 2px 8px rgba(0, 0, 0, 0.04)',
    },
    // 导航栏
    nav: {
      default: 'none',
      scrolled: '0 1px 2px rgba(0, 0, 0, 0.04)',
    },
    // 模态框
    modal: '0 30px 60px rgba(0, 0, 0, 0.12), 0 12px 24px rgba(0, 0, 0, 0.08)',
    // 浮动按钮
    fab: '0 4px 12px rgba(0, 0, 0, 0.12), 0 2px 4px rgba(0, 0, 0, 0.06)',
    // Tooltip
    tooltip: '0 4px 8px rgba(0, 0, 0, 0.10), 0 2px 4px rgba(0, 0, 0, 0.05)',
  },
} as const;

export type Shadows = typeof shadows;

// ---- Apple Liquid Glass (WWDC25 新设计语言) ----
// Liquid Glass 是 Apple 在 WWDC25 引入的新材质语言
// 核心特征：动态半透明玻璃、色彩漂移、景深分层、环境响应
/**
 * Liquid Glass 设计规格 (基于 WWDC25 官方演示)：
 * - 背景模糊: 20-40px (backdrop-filter: blur)
 * - 饱和度增强: 1.1-1.2 倍
 * - 色彩叠加: 从背景取色，叠加 5-15% 透明度
 * - 动态边框: 0.5px 明亮高光 + 0.5px 暗部描边
 * - 景深分层: 多层模糊叠加创造 Z 轴感
 */
export const liquidGlass = {
  /** 玻璃材质 - 浅色模式 */
  light: {
    background: 'rgba(255, 255, 255, 0.72)',
    borderTop: 'rgba(255, 255, 255, 0.5)',
    borderBottom: 'rgba(0, 0, 0, 0.04)',
    blur: '20px',
    saturate: 1.1,
  },
  /** 玻璃材质 - 深色模式 */
  dark: {
    background: 'rgba(28, 28, 30, 0.72)',
    borderTop: 'rgba(255, 255, 255, 0.06)',
    borderBottom: 'rgba(0, 0, 0, 0.3)',
    blur: '30px',
    saturate: 1.2,
  },
  /** 高透明度玻璃（浮层/模态框） */
  elevated: {
    background: 'rgba(255, 255, 255, 0.82)',
    blur: '40px',
    saturate: 1.15,
  },
  /** CSS 片段 */
  cssTemplate: `
    /* Liquid Glass - Light Mode */
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    background: rgba(255, 255, 255, 0.72);
    border-top: 0.5px solid rgba(255, 255, 255, 0.5);
    border-bottom: 0.5px solid rgba(0, 0, 0, 0.04);

    /* Liquid Glass - Dark Mode */
    @media (prefers-color-scheme: dark) {
      background: rgba(28, 28, 30, 0.72);
      border-top: 0.5px solid rgba(255, 255, 255, 0.06);
      border-bottom: 0.5px solid rgba(0, 0, 0, 0.3);
      backdrop-filter: blur(30px);
      -webkit-backdrop-filter: blur(30px);
    }
  `,
} as const;

export default shadows;
