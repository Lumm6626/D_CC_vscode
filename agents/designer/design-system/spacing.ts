// Design System - Spacing / Layout / Grids
// 基于 Apple 官方布局规范 + apple.com 响应式布局分析
// 来源：
//   - 8px 网格系统: Apple HIG Layout
//   - 安全区 44px/48px: iOS HIG / visionOS HIG
//   - 触摸目标: Apple HIG (最小 44pt)
//   - 内容最大宽度 1068px/980px/692px: Apple.com 响应式布局分析
//   - 断点: Apple.com 多设备实测
// 交叉验证文件: source-references.md
//
// Apple 官网布局核心规则：
// 1. 8px 网格系统 (8px Grid System) - 所有间距都基于 8 的倍数
// 2. 内容安全区：页面左右保持 20-24px 的边距（响应式下）
// 3. 段落间距：正文段落之间 24px（3 × 8px 网格）
// 4. 标题与内容间距：标题下 16px
// 5. 最小触摸目标：44pt（Apple HIG 交互规范）
// 6. Section 间距：页面模块之间 80-120px

export const spacing = {
  // ---- 8px 网格系统 ----
  '0': '0px',
  'px': '1px',
  '0.5': '2px',      // ½ 网格（细边框、微间距）
  '1': '4px',         // ½ 网格（内边距压缩态）
  '2': '8px',         // 1 网格（元素间距基准单位）
  '3': '12px',        // 1.5 网格（紧凑间距）
  '4': '16px',        // 2 网格（标准间距，内容与边框）
  '5': '20px',        // 2.5 网格（Apple 官网内容边距）
  '6': '24px',        // 3 网格（段落间距、卡片内边距）
  '7': '28px',        // 3.5 网格
  '8': '32px',        // 4 网格（大间距）
  '9': '36px',        // 4.5 网格
  '10': '40px',       // 5 网格（模块间距）
  '11': '44px',       // 5.5 网格（最小触摸目标 44pt）
  '12': '48px',       // 6 网格（大模块间距）
  '14': '56px',       // 7 网格
  '16': '64px',       // 8 网格（Apple 官网 Section 间距）
  '18': '72px',       // 9 网格
  '20': '80px',       // 10 网格（Apple 官网产品间距）
  '24': '96px',       // 12 网格
  '28': '112px',
  '30': '120px',      // 15 网格（Apple 官网大 Sections 间距）
  '32': '128px',
  '36': '144px',
  '40': '160px',
} as const;

export type Spacing = typeof spacing;

// ---- Apple 响应式断点 (基于 apple.com 实际 - 标准) ----
export const breakpoints = {
  /** 手机竖屏 (< 375px iPhone SE) */
  xs: '375px',
  /** 手机横屏 / 小屏手机 */
  sm: '480px',
  /** 大屏手机 / 小屏平板 (iPad mini) */
  md: '768px',
  /** 平板竖屏 (iPad) */
  lg: '1024px',
  /** 小桌面 / 平板横屏 */
  xl: '1280px',
  /** 大桌面 */
  '2xl': '1440px',
  /** Apple 官网最大内容宽度 */
  '3xl': '1680px',
} as const;

export type Breakpoints = typeof breakpoints;

// ---- Apple 官网内容最大宽度 ----
export const maxWidths = {
  /** 常规内容区最大宽度（Apple 官网主要用 980px-1068px） */
  content: '1068px',
  /** 大内容区 */
  contentLarge: '1440px',
  /** Hero 全宽区域 */
  hero: '100%',
  /** 栅格卡片区 */
  gridContent: '980px',
  /** 窄内容区（导购/辅助页） */
  contentNarrow: '680px',
} as const;

// ---- 语义化间距别名 ----
export const semanticSpacing = {
  // 页面级
  'page-padding': spacing['5'],        // 手机页面左右边距 20px
  'page-padding-lg': spacing['8'],     // 桌面页面左右边距 32px
  'section-gap': spacing['20'],        // 页面模块间距 80px
  'section-gap-lg': spacing['30'],     // 大模块间距 120px
  // 卡片级
  'card-padding': spacing['6'],        // 卡片内边距 24px
  'card-gap': spacing['4'],            // 卡片间距 16px
  // 内容级
  'paragraph-gap': spacing['6'],       // 段落间距 24px
  'title-content-gap': spacing['4'],   // 标题与内容间距 16px
  'label-input-gap': spacing['2'],     // 标签与输入框间距 8px
  // 按钮
  'button-padding-x': spacing['6'],    // 按钮水平内边距 24px
  'button-padding-y': spacing['3'],    // 按钮垂直内边距 12px
  'button-gap': spacing['3'],          // 按钮间距 12px
  // 最小触摸目标
  'touch-target': '44px',              // Apple HIG 最小触摸面积 44pt
};

// ---- TailwindCSS 扩展 ----
export const tailwindSpacing = {
  ...spacing,
};

export default spacing;
