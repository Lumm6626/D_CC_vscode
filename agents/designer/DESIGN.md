# UI Designer Subagent 设计规范

## 概述

- **Agent名称**: UI Designer Subagent
- **职责**: 为网站、小程序、App提供UI/UX设计服务
- **设计标准**: Apple Design Language (HIG)
- **输出格式**: 设计规范文档 + 可运行React代码 + 交互规格说明

---

## 设计原则

1. **极简主义** - 减少视觉噪音，突出内容
2. **一致性** - 统一的视觉语言和交互模式
3. **层次感** - 通过阴影、间距、动效表达层级
4. **细节打磨** - 像素级精确，严格遵循8px网格系统

---

## 色彩系统

### 主色 (Primary)

| 名称 | 色值 | 用途 |
|------|------|------|
| Blue | `#007AFF` | 主要操作按钮、链接、强调 |
| Purple | `#5856D6` | 次要强调、品牌色 |
| Pink | `#FF2D55` | 警示、特殊操作 |

### 语义色 (Semantic)

| 名称 | 色值 | 用途 |
|------|------|------|
| Success | `#34C759` | 成功状态、正向反馈 |
| Warning | `#FF9500` | 警告状态、注意提示 |
| Error | `#FF3B30` | 错误状态、危险操作 |
| Info | `#5AC8FA` | 信息提示 |

### 中性色 (Neutral)

| 名称 | 色值 | 用途 |
|------|------|------|
| Black | `#1D1D1F` | 主要文字 |
| Dark | `#272730` | 深色背景 |
| Gray | `#86868B` | 次要文字、占位符 |
| LightGray | `#D2D2D7` | 边框、分割线 |
| UltraLight | `#F5F5F7` | 页面背景、卡片背景 |
| White | `#FFFFFF` | 卡片、容器背景 |

### 深色模式 (Dark Mode)

| 用途 | 色值 |
|------|------|
| Background | `#000000`, `#1D1D1F`, `#2C2C2E` |
| Surface | `#3A3A3C`, `#48484A` |
| Text | `#FFFFFF`, `rgba(235, 235, 245, 0.9)`, `rgba(235, 235, 245, 0.6)` |

---

## 字体系统

### 字体族 (Font Family)

| 用途 | 字体栈 |
|------|--------|
| Display | `-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif` |
| Text | `-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', sans-serif` |
| Mono | `'SF Mono', 'Fira Code', 'Consolas', monospace` |

### 字号 (Font Size)

| 名称 | 数值 | 用途 |
|------|------|------|
| xs | 12px | 辅助文字、标签 |
| sm | 14px | 次要文字 |
| base | 16px | 正文（基准） |
| lg | 18px | 强调文字 |
| xl | 20px | 区块标题 |
| 2xl | 24px | 页面标题 |
| 3xl | 30px | 大标题 |
| 4xl | 36px | 特大标题 |
| 5xl | 48px | Hero标题 |

### 字重 (Font Weight)

| 名称 | 数值 | 用途 |
|------|------|------|
| regular | 400 | 正文 |
| medium | 500 | 次要强调 |
| semibold | 600 | 标题 |
| bold | 700 | 重要强调 |

### 行高 (Line Height)

| 名称 | 数值 | 用途 |
|------|------|------|
| tight | 1.2 | 标题 |
| normal | 1.5 | 正文 |
| relaxed | 1.75 | 长文本 |

---

## 间距系统

遵循8px网格系统：

| 名称 | 数值 | 用途 |
|------|------|------|
| 0 | 0px | 无间距 |
| px | 1px | 细线 |
| 0.5 | 2px | 紧凑间距 |
| 1 | 4px | 元素内部间距 |
| 2 | 8px | 小元素间距 |
| 3 | 12px | 中等间距 |
| 4 | 16px | 标准间距（基准） |
| 5 | 20px | 稍大间距 |
| 6 | 24px | 区块间距 |
| 8 | 32px | 大区块间距 |
| 10 | 40px | 容器间距 |
| 12 | 48px | 页面级间距 |
| 16 | 64px | 大页面间距 |
| 20 | 80px | 页面分隔 |
| 24 | 96px | 超大间距 |

---

## 圆角系统

| 名称 | 数值 | 用途 |
|------|------|------|
| none | 0px | 无圆角 |
| sm | 4px | 小标签、CHECKBOX |
| md | 8px | 按钮、小卡片 |
| lg | 12px | 输入框、中卡片 |
| xl | 16px | 大卡片 |
| 2xl | 20px | 模态框 |
| 3xl | 24px | 大容器 |
| full | 9999px | 圆形、胶囊按钮 |

---

## 阴影系统

| 名称 | 数值 | 用途 |
|------|------|------|
| sm | `0 1px 2px rgba(0, 0, 0, 0.05)` | 轻微阴影、默认卡片 |
| base | `0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)` | 标准卡片 |
| md | `0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06)` | 悬停状态 |
| lg | `0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05)` | 浮层、dropdown |
| xl | `0 20px 25px rgba(0, 0, 0, 0.1), 0 10px 10px rgba(0, 0, 0, 0.04)` | 模态框 |
| 2xl | `0 25px 50px rgba(0, 0, 0, 0.25)` | 全屏模态框 |
| inner | `inset 0 2px 4px rgba(0, 0, 0, 0.06)` | 输入框内阴影 |

---

## 动效系统

### 时长 (Transition Duration)

| 名称 | 数值 | 用途 |
|------|------|------|
| fast | 150ms | 微交互、按钮状态 |
| normal | 250ms | 标准过渡 |
| slow | 400ms | 页面过渡、模态框 |
| spring | 500ms | 弹性动画 |

### 缓动函数 (Easing)

| 名称 | 数值 | 用途 |
|------|------|------|
| default | `cubic-bezier(0.4, 0, 0.2, 1)` | 标准缓动 |
| in | `cubic-bezier(0.4, 0, 1, 1)` | 入场动画 |
| out | `cubic-bezier(0, 0, 0.2, 1)` | 出场动画 |
| inOut | `cubic-bezier(0.4, 0, 0.2, 1)` | 往返动画 |
| spring | `cubic-bezier(0.175, 0.885, 0.32, 1.275)` | 弹性动效 |

---

## 组件规范

### 按钮 (Button)

#### Primary Button

| 状态 | 背景色 | 文字色 | 阴影 | 变换 |
|------|--------|--------|------|------|
| Default | `#007AFF` | `#FFFFFF` | `0 1px 3px rgba(0,0,0,0.1)` | - |
| Hover | `#0078F5` | `#FFFFFF` | `0 4px 12px rgba(0,0,0,0.15)` | `scale(1.02)` |
| Active | `#0066D6` | `#FFFFFF` | `0 1px 2px rgba(0,0,0,0.1)` | `scale(0.98)` |
| Disabled | `#007AFF` | `rgba(255,255,255,0.5)` | none | - |
| Loading | `#007AFF` | - | - | 显示spinner |

#### Secondary Button

| 状态 | 背景色 | 文字色 | 边框 | 阴影 |
|------|--------|--------|------|------|
| Default | `transparent` | `#007AFF` | `1px solid #007AFF` | none |
| Hover | `rgba(0,122,255,0.1)` | `#0078F5` | `1px solid #0078F5` | - |
| Active | `rgba(0,122,255,0.2)` | `#0066D6` | `1px solid #0066D6` | - |
| Disabled | `transparent` | `rgba(0,122,255,0.3)` | `1px solid rgba(0,122,255,0.3)` | - |

#### 按钮动效

```typescript
const buttonHover = {
  scale: 1.02,
  transition: { duration: 0.15, ease: 'ease-out' }
}

const buttonActive = {
  scale: 0.98,
  transition: { duration: 0.1, ease: 'ease-out' }
}
```

### 输入框 (Input)

| 状态 | 边框色 | 背景色 | 阴影 | 说明 |
|------|--------|--------|------|------|
| Default | `#D2D2D7` | `#FFFFFF` | `inset 0 1px 2px rgba(0,0,0,0.06)` | - |
| Hover | `#86868B` | `#FFFFFF` | - | 边框颜色变深 |
| Focus | `#007AFF` | `#FFFFFF` | `0 0 0 3px rgba(0,122,255,0.2)` | 蓝色光圈 |
| Error | `#FF3B30` | `#FFFFFF` | `0 0 0 3px rgba(255,59,48,0.2)` | 红色光圈 |
| Disabled | `#F5F5F7` | `#F5F5F7` | none | 灰色背景 |

### 卡片 (Card)

| 状态 | 阴影 | 变换 | 说明 |
|------|------|------|------|
| Default | `0 1px 3px rgba(0,0,0,0.08)` | - | - |
| Hover | `0 12px 40px rgba(0,0,0,0.12)` | `translateY(-2px)` | 上浮效果 |

---

## 交互规格

### 页面过渡动画

| 动画 | 时长 | 缓动 | 说明 |
|------|------|------|------|
| 入场 | 400ms | `cubic-bezier(0, 0, 0.2, 1)` | fade + slideUp |
| 出场 | 200ms | `cubic-bezier(0.4, 0, 1, 1)` | fade |
| 页面切换 | 400ms | `cubic-bezier(0.4, 0, 0.2, 1)` | slide + fade |

### Framer Motion 预设

```typescript
const springTransition = {
  type: "spring",
  stiffness: 300,
  damping: 30
}

const smoothTransition = {
  type: "tween",
  duration: 0.25,
  ease: [0.4, 0, 0.2, 1]
}
```

### 手势反馈

| 手势 | 反馈 | 触觉 |
|-----|------|------|
| 点击 | 缩放动画 + 颜色变化 | 轻触反馈 |
| 长按 | 显示工具提示/上下文菜单 | 中触反馈 |
| 滑动 | 切换页面/显示操作按钮 | 轻触反馈 |

---

## 异常状态

### 空状态
- 显示空状态插图
- 配合说明文字
- 提供操作入口

### 加载状态
- 骨架屏优先
- 显示加载指示器
- 保持布局稳定

### 错误状态
- 友好错误提示
- 提供重试入口
- 不显示技术细节

### 断网状态
- 显示断网提示
- 缓存数据展示
- 离线操作队列

---

## 输出物清单

### 1. 设计规范文档 (Markdown)
- [色彩系统](#色彩系统)
- [字体系统](#字体系统)
- [间距系统](#间距系统)
- [组件规格](#组件规范)
- [交互规格](#交互规格)

### 2. 可运行UI代码
- React + TailwindCSS + Framer Motion
- TypeScript类型
- 完整的交互动效

### 3. 交互规格说明 (可选)
- 状态变化
- 动画参数
- 手势反馈

### 4. API契约文档 (可选)
- 当项目需要前后端并行开发时输出
- 使用 `templates/api-contract.md` 模板

---

## 设计检查清单

- [ ] 色彩对比度满足WCAG AA标准 (4.5:1)
- [ ] 遵循8px网格系统
- [ ] 按钮有清晰的默认/悬停/激活/禁用状态
- [ ] 输入框有聚焦态和错误态
- [ ] 卡片悬停有上浮动效
- [ ] 动画时长合理（150ms-400ms）
- [ ] 触觉反馈与视觉反馈一致
- [ ] 深色模式适配完整