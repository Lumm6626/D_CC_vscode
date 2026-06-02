// Design System - Typography
// 基于 Apple 官方字体规范
// 来源：
//   - 字体家族: Apple HIG Typography + Apple Font Documentation
//   - 字号阶梯: iOS Dynamic Type 11 级 (Large size)
//   - Tracking/Letter-spacing: WWDC20 'The details of UI typography'
//   - SF Pro Display vs Text 分界线: ≥20pt / <20pt (Apple 官方定义)
// 交叉验证文件: source-references.md

/**
 * Apple SF Pro 字体核心规则：
 * - SF Pro 是可变字体（Variable Font），支持 Weight / Width / Optical Size 三轴
 * - SF Pro Display：用于 ≥20pt 的大字号标题（间距更紧，光学优化大字号）
 * - SF Pro Text：用于 <20pt 的正文字号（间距更松，优化小字号可读性）
 * - SF Pro Rounded：圆角变体，用于友好/趣味性 UI
 * - SF Mono：等宽字体，用于代码
 * - 中文环境下 fallback 到系统苹方（PingFang SC）
 * - 中文字体也遵循 SF 的视觉对齐原则，苹方 (PingFang SC) 与 SF Pro 视觉匹配
 */

export const typography = {
  // ---- 字体族 (Font Families) ----
  fontFamily: {
    /** 
     * Apple 官网英文用 SF Pro Display（标题），中文 fallback 苹方
     * 注意：apple.com.cn 使用相同的 SF Pro + PingFang SC 混合栈
     */
    display: [
      "'SF Pro Display'",       // ≥20pt 标题用
      "'SF Pro Text'",          // 回退
      "'PingFang SC'",          // 中文场景主字体（苹方，与 SF 视觉配对）
      "'Helvetica Neue'",       // 次级回退
      "'Helvetica'",            // 次级回退
      'Arial',
      'sans-serif',
    ].join(', '),

    /**
     * Apple 官网正文用 SF Pro Text
     * 中英文混合排版时 SF Pro Text 与 PingFang SC 组合
     */
    text: [
      "'SF Pro Text'",          // <20pt 正文用
      "'PingFang SC'",
      "'Helvetica Neue'",
      "'Helvetica'",
      'Arial',
      'sans-serif',
    ].join(', '),

    /** 等宽字体 - 用于代码、数字 */
    mono: [
      "'SF Mono'",
      "'Fira Code'",
      "'SF Pro Text'",
      "'PingFang SC'",
      'Consolas',
      'monospace',
    ].join(', '),

    /** 圆角变体 - 用于友好的 UI 元素 */
    rounded: [
      "'SF Pro Rounded'",
      "'PingFang SC'",
      "'Helvetica Neue'",
      'sans-serif',
    ].join(', '),
  },

  // ---- 字号阶梯 (Font Size Scale) ----
  // 对标 Apple Dynamic Type 11 级字号系统
  fontSize: {
    /** 脚注、辅助文字 - SF Pro Text */
    caption2: '11px',     // iOS Dynamic Type caption2
    caption1: '12px',     // iOS Dynamic Type caption1
    footnote: '13px',     // iOS Dynamic Type footnote（Apple 官网表格说明）
    /** 正文 */
    callout: '14px',      // iOS Dynamic Type callout（Apple 官网二级正文）
    body: '17px',         // iOS Dynamic Type body（Apple 官网正文基值）
    /** 标题 */
    headline: '17px',     // iOS Dynamic Type headline（正文加粗版）
    subheadline: '15px',  // iOS 二级标题
    title3: '20px',       // iOS Dynamic Type title3（Apple 官网 section 标题）
    title2: '22px',       // iOS Dynamic Type title2
    title1: '28px',       // iOS Dynamic Type title1
    /** 大标题 */
    largeTitle: '34px',   // iOS Dynamic Type largeTitle（Apple 官网产品页主标题）
    hero: '48px',         // Apple 官网 Hero 标题（iPhone 页）
    heroLarge: '56px',    // Apple 官网大 Hero
    heroXLarge: '64px',   // Apple 官网特大标题（Vision Pro 页）
    display: '80px',      // Apple 特殊展示用超大字号
  },

  // ---- 字重 (Font Weights) ----
  fontWeight: {
    thin: 100,
    ultraLight: 200,
    light: 300,
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    heavy: 800,
    black: 900,
  },

  // ---- 行高 (Line Heights) ----
  lineHeight: {
    /**
     * Apple 官网行高规则：
     * - 标题 <24pt: line-height 1.2-1.3
     * - 正文 14-17pt: line-height 1.47（Apple 官网实际值 ≈1.47）
     * - 长文: line-height 1.6-1.8
     */
    none: 1,
    tight: 1.15,      // 大标题（largeTitle, hero）
    snug: 1.3,        // 小标题
    normal: 1.47,     // 正文（Apple 官网 body 实际行高 ≈1.47059）
    relaxed: 1.6,     // 长文本
    loose: 1.8,       // 宽松排版
  },

  // ---- 字距 (Letter Spacing / Tracking) ----
  /**
   * Apple SF Pro 关键字距规则（WWDC 2020 技术详解）：
   * - SF Pro Text (<20pt): tracking 随字号从 17pt→13pt 逐渐变松
   * - SF Pro Display (≥20pt): tracking 从 20pt→∞ 逐渐变紧（负值）
   * - 中文字体（苹方）不需要 tracking 调整
   */
  letterSpacing: {
    caption2: '0.07em',     // 11pt - 小幅增加
    caption1: '0.03em',     // 12pt
    footnote: '0.01em',     // 13pt
    callout: '-0.01em',     // 14pt
    body: '-0.02em',        // 17pt
    title3: '0em',          // 20pt - SF Pro Display 起始点
    title2: '-0.02em',      // 22pt
    title1: '-0.03em',      // 28pt - 约 -0.8px
    largeTitle: '-0.04em',  // 34pt
    hero: '-0.05em',        // 48pt
    display: '-0.06em',     // 80pt
  },
} as const;

export type Typography = typeof typography;

// ---- 语义化字号别名（方便直接使用） ----
export const semanticFontSize = {
  // Apple 官网常用语义
  'hero-title': typography.fontSize.hero,
  'product-title': typography.fontSize.largeTitle,
  'section-title': typography.fontSize.title1,
  'card-title': typography.fontSize.title3,
  'body-text': typography.fontSize.body,
  'callout-text': typography.fontSize.callout,
  'footnote-text': typography.fontSize.footnote,
  'caption-text': typography.fontSize.caption1,
};

// ---- TailwindCSS 扩展配置 ----
export const tailwindTypography = {
  fontFamily: {
    'sf-display': [
      "'SF Pro Display'",
      "'PingFang SC'",
      "'Helvetica Neue'",
      'sans-serif',
    ].join(', '),
    'sf-text': [
      "'SF Pro Text'",
      "'PingFang SC'",
      "'Helvetica Neue'",
      'sans-serif',
    ].join(', '),
    'sf-mono': "'SF Mono', 'Fira Code', 'Consolas', monospace",
  },
  fontSize: {
    'caption2': ['11px', { lineHeight: '13px', letterSpacing: '0.07em' }],
    'caption1': ['12px', { lineHeight: '16px', letterSpacing: '0.03em' }],
    'footnote': ['13px', { lineHeight: '18px', letterSpacing: '0.01em' }],
    'callout': ['14px', { lineHeight: '20px', letterSpacing: '-0.01em' }],
    'body': ['17px', { lineHeight: '25px', letterSpacing: '-0.02em' }],
    'title3': ['20px', { lineHeight: '25px' }],
    'title2': ['22px', { lineHeight: '28px', letterSpacing: '-0.02em' }],
    'title1': ['28px', { lineHeight: '34px', letterSpacing: '-0.03em' }],
    'large-title': ['34px', { lineHeight: '41px', letterSpacing: '-0.04em' }],
    'hero': ['48px', { lineHeight: '54px', letterSpacing: '-0.05em' }],
    'hero-large': ['56px', { lineHeight: '60px', letterSpacing: '-0.05em' }],
  },
};

export default typography;
