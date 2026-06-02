"""工具栏按钮定义、命中检测、图标渲染."""

import math
from dataclasses import dataclass
from enum import Enum, auto
from PySide6.QtCore import QRect, QPoint, Qt
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics, QPainterPath, QCursor, QPixmap,
)
from utils import hex_to_qcolor


class ToolbarAction(Enum):
    COLOR = auto()
    RECT = auto()
    CIRCLE = auto()
    ARROW = auto()
    LINE_WIDTH = auto()
    TEXT = auto()
    FONT_SIZE = auto()
    MOSAIC = auto()
    UNDO = auto()
    SAVE = auto()
    CONFIRM = auto()
    CANCEL = auto()


ANNOTATION_COLORS = [
    ("#FF3B30", "红"), ("#FF9500", "橙"), ("#FFCC00", "黄"),
    ("#34C759", "绿"), ("#007AFF", "蓝"), ("#FFFFFF", "白"),
]

LINE_WIDTHS = [1, 2, 3, 4, 5, 6]
FONT_SIZES = [12, 14, 16, 18, 20, 24, 28, 32]

TOOLTIPS = {
    ToolbarAction.COLOR: "颜色",
    ToolbarAction.RECT: "矩形",
    ToolbarAction.CIRCLE: "圆形",
    ToolbarAction.ARROW: "箭头",
    ToolbarAction.LINE_WIDTH: "线宽",
    ToolbarAction.TEXT: "文字",
    ToolbarAction.FONT_SIZE: "字号",
    ToolbarAction.MOSAIC: "马赛克",
    ToolbarAction.UNDO: "撤销",
    ToolbarAction.SAVE: "保存",
    ToolbarAction.CONFIRM: "确认",
    ToolbarAction.CANCEL: "取消",
}


@dataclass
class ToolbarButton:
    action: ToolbarAction
    rect: QRect = QRect()
    selected: bool = False


class ToolbarLayout:
    BTN = 42
    GAP = 3
    PAD_H = 7
    PAD_V = 6
    RADIUS = 9
    SEP_W = 14

    BG = QColor(38, 38, 38)
    SELECTED = QColor(26, 115, 232)
    ICON = QColor(220, 220, 220)
    SEP = QColor(75, 75, 75)

    LAYOUT = [
        ToolbarAction.COLOR,
        None,
        ToolbarAction.RECT, ToolbarAction.CIRCLE, ToolbarAction.ARROW, ToolbarAction.LINE_WIDTH,
        None,
        ToolbarAction.TEXT, ToolbarAction.FONT_SIZE, ToolbarAction.MOSAIC,
        None,
        ToolbarAction.UNDO,
        None,
        ToolbarAction.SAVE, ToolbarAction.CONFIRM, ToolbarAction.CANCEL,
    ]

    def __init__(self):
        self.buttons: list[ToolbarButton] = []
        self.color_panel_rect = QRect()
        self.color_panel_visible = False
        self.line_width_popup_rect = QRect()
        self.line_width_popup_visible = False
        self.font_size_popup_rect = QRect()
        self.font_size_popup_visible = False
        self.line_width = 2
        self.font_size = 14
        self.selected_action: ToolbarAction | None = None
        self.current_color = "#FF3B30"
        self.rect = QRect()
        self.hovered_action: ToolbarAction | None = None

    def build(self, target_region: QRect, selected_tool: ToolbarAction | None,
              line_width: int, font_size: int, current_color: str):
        self.selected_action = selected_tool
        self.line_width = line_width
        self.font_size = font_size
        self.current_color = current_color
        self.buttons.clear()

        n_seps = sum(1 for a in self.LAYOUT if a is None)
        n_btns = len(self.LAYOUT) - n_seps
        total_width = (n_btns * self.BTN + (n_btns - 1) * self.GAP
                       + n_seps * self.SEP_W + 2 * self.PAD_H)
        total_height = self.BTN + 2 * self.PAD_V

        rx, ry, rw, rh = target_region.x(), target_region.y(), target_region.width(), target_region.height()
        x = rx + (rw - total_width) // 2
        y = ry + rh + 8
        if y + total_height + 200 > ry + rh + 300:
            y = ry - total_height - 8
        if x < 0:
            x = 4

        self.rect = QRect(x, y, total_width, total_height)

        cx = x + self.PAD_H
        cy = y + self.PAD_V
        for action in self.LAYOUT:
            if action is None:
                cx += self.SEP_W
                continue
            btn = ToolbarButton(
                action=action,
                rect=QRect(cx, cy, self.BTN, self.BTN),
                selected=(action == selected_tool and action not in (
                    ToolbarAction.COLOR, ToolbarAction.LINE_WIDTH, ToolbarAction.FONT_SIZE,
                )),
            )
            self.buttons.append(btn)
            cx += self.BTN + self.GAP

        self._layout_color_panel()
        self._layout_line_width_popup()
        self._layout_font_size_popup()

    def _layout_color_panel(self):
        cs, cg = 22, 6
        n = len(ANNOTATION_COLORS)
        pw = n * cs + (n + 1) * cg
        ph = cs + 2 * cg
        btn = self._find_btn(ToolbarAction.COLOR)
        px = btn.rect.x() - (pw - self.BTN) // 2 if btn else self.rect.x() + 4
        py = self.rect.top() - ph - 6
        self.color_panel_rect = QRect(px, py, pw, ph)

    def _layout_line_width_popup(self):
        """线宽弹出面板：竖向排列不同粗细的横线."""
        n = len(LINE_WIDTHS)
        item_h = 20; gap = 2
        pw = 52
        ph = n * item_h + (n - 1) * gap + 16
        btn = self._find_btn(ToolbarAction.LINE_WIDTH)
        if btn:
            px = btn.rect.center().x() - pw // 2
            py = self.rect.top() - ph - 6
            self.line_width_popup_rect = QRect(px, py, pw, ph)

    def _layout_font_size_popup(self):
        """字号弹出面板：竖向排列不同大小的 A."""
        n = len(FONT_SIZES)
        item_h = 22; gap = 2
        pw = 56
        ph = n * item_h + (n - 1) * gap + 16
        btn = self._find_btn(ToolbarAction.FONT_SIZE)
        if btn:
            px = btn.rect.center().x() - pw // 2
            py = self.rect.top() - ph - 6
            self.font_size_popup_rect = QRect(px, py, pw, ph)

    def _find_btn(self, action: ToolbarAction) -> ToolbarButton | None:
        for b in self.buttons:
            if b.action == action:
                return b
        return None

    # ═══════════════════════════════════════════════════════
    #  命中检测
    # ═══════════════════════════════════════════════════════

    def hit_test(self, pos: QPoint) -> ToolbarAction | None:
        for btn in self.buttons:
            if btn.rect.contains(pos):
                return btn.action
        return None

    def set_hovered(self, pos: QPoint):
        """更新鼠标悬停按钮."""
        self.hovered_action = self.hit_test(pos)

    def hit_color(self, pos: QPoint) -> str | None:
        if not self.color_panel_visible:
            return None
        cs, cg = 22, 6
        p = self.color_panel_rect
        rx, ry = pos.x() - p.x(), pos.y() - p.y()
        if cg <= ry <= cg + cs:
            for i, (c, _) in enumerate(ANNOTATION_COLORS):
                bx = cg + i * (cs + cg)
                if bx <= rx <= bx + cs:
                    return c
        return None

    def hit_line_width(self, pos: QPoint) -> int | None:
        """在线宽弹出面板中检测选中的线宽，未命中返回 None."""
        if not self.line_width_popup_visible:
            return None
        p = self.line_width_popup_rect
        if not p.contains(pos):
            return None
        n = len(LINE_WIDTHS)
        item_h = 20; gap = 2; pad = 8
        ry = pos.y() - p.y() - pad
        idx = ry // (item_h + gap)
        if 0 <= idx < n:
            return LINE_WIDTHS[idx]
        return None

    def hit_font_size(self, pos: QPoint) -> int | None:
        """在字号弹出面板中检测选中的字号."""
        if not self.font_size_popup_visible:
            return None
        p = self.font_size_popup_rect
        if not p.contains(pos):
            return None
        n = len(FONT_SIZES)
        item_h = 22; gap = 2; pad = 8
        ry = pos.y() - p.y() - pad
        idx = ry // (item_h + gap)
        if 0 <= idx < n:
            return FONT_SIZES[idx]
        return None

    # ═══════════════════════════════════════════════════════
    #  渲染入口
    # ═══════════════════════════════════════════════════════

    def render(self, painter: QPainter):
        if self.rect.isEmpty():
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        path = QPainterPath()
        path.addRoundedRect(self.rect.x(), self.rect.y(), self.rect.width(), self.rect.height(),
                            self.RADIUS, self.RADIUS)
        painter.fillPath(path, self.BG)

        # 分隔线
        cx = self.rect.x() + self.PAD_H
        for action in self.LAYOUT:
            if action is not None:
                cx += self.BTN + self.GAP
            else:
                sx = cx + self.SEP_W // 2
                sy1 = self.rect.y() + self.PAD_V + 7
                sy2 = self.rect.y() + self.PAD_V + self.BTN - 7
                painter.setPen(QPen(self.SEP, 1))
                painter.drawLine(sx, sy1, sx, sy2)
                cx += self.SEP_W

        if self.line_width_popup_visible:
            self._draw_line_width_popup(painter)
        if self.font_size_popup_visible:
            self._draw_font_size_popup(painter)
        if self.color_panel_visible:
            self._draw_color_panel(painter)

        for btn in self.buttons:
            self._draw_btn(painter, btn)

        # 悬停提示
        if self.hovered_action and not self.color_panel_visible and \
           not self.line_width_popup_visible and not self.font_size_popup_visible:
            self._draw_tooltip(painter)

        painter.restore()

    def _draw_btn(self, p: QPainter, btn: ToolbarButton):
        r = btn.rect
        if btn.selected:
            p.fillRect(r, self.SELECTED)
        p.save(); p.translate(r.x(), r.y()); w, h = self.BTN, self.BTN
        {
            ToolbarAction.COLOR:       self._ic_color,
            ToolbarAction.RECT:        self._ic_rect,
            ToolbarAction.CIRCLE:      self._ic_circle,
            ToolbarAction.ARROW:       self._ic_arrow,
            ToolbarAction.LINE_WIDTH:  self._ic_line_width,
            ToolbarAction.TEXT:        self._ic_text,
            ToolbarAction.FONT_SIZE:   self._ic_font_size,
            ToolbarAction.MOSAIC:      self._ic_mosaic,
            ToolbarAction.UNDO:        self._ic_undo,
            ToolbarAction.SAVE:        self._ic_save,
            ToolbarAction.CONFIRM:     self._ic_confirm,
            ToolbarAction.CANCEL:      self._ic_cancel,
        }[btn.action](p, w, h)
        p.restore()

    # ═══════════════════════════════════════════════════════
    #  图标 (42×42)
    # ═══════════════════════════════════════════════════════

    def _ic_color(self, p: QPainter, w: int, h: int):
        c = hex_to_qcolor(self.current_color); r = 11
        p.setBrush(c)
        p.setPen(QPen(QColor(140, 140, 140), 1.5) if self.current_color.upper() == "#FFFFFF" else Qt.PenStyle.NoPen)
        p.drawEllipse(w // 2 - r, h // 2 - r, r * 2, r * 2)

    def _ic_rect(self, p: QPainter, w: int, h: int):
        pen = QPen(self.ICON, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush); m = 10
        p.drawRoundedRect(m, m, w - 2 * m, h - 2 * m, 3, 3)

    def _ic_circle(self, p: QPainter, w: int, h: int):
        pen = QPen(self.ICON, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush); m = 10
        p.drawEllipse(m, m, w - 2 * m, h - 2 * m)

    def _ic_arrow(self, p: QPainter, w: int, h: int):
        pen = QPen(self.ICON, 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen); m = 10
        p.drawLine(m, h - m, w - m, m)
        angle = math.atan2((h - m) - m, (w - m) - m); al = 11; tip = QPoint(w - m, m)
        p.setBrush(self.ICON); p.setPen(Qt.PenStyle.NoPen)
        tri = QPainterPath(); tri.moveTo(tip)
        tri.lineTo(QPoint(int(tip.x() + al * math.cos(angle + math.radians(155))),
                          int(tip.y() - al * math.sin(angle + math.radians(155)))))
        tri.lineTo(QPoint(int(tip.x() + al * math.cos(angle - math.radians(155))),
                          int(tip.y() - al * math.sin(angle - math.radians(155)))))
        tri.closeSubpath(); p.drawPath(tri)

    def _ic_line_width(self, p: QPainter, w: int, h: int):
        # 三条不同粗细的线叠在一起表示"线宽"概念
        cy = h // 2
        for i, lw in enumerate([1, 3, 5]):
            pen = QPen(self.ICON, lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            y = cy - 5 + i * 5
            p.drawLine(8, y, w - 8, y)

    def _ic_text(self, p: QPainter, w: int, h: int):
        p.setPen(self.ICON)
        p.setFont(QFont("Microsoft YaHei", 17, QFont.Weight.Bold))
        p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "T")

    def _ic_font_size(self, p: QPainter, w: int, h: int):
        p.setPen(self.ICON)
        p.setFont(QFont("Microsoft YaHei", 15, QFont.Weight.Bold))
        p.drawText(QRect(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "A")

    def _ic_mosaic(self, p: QPainter, w: int, h: int):
        """马赛克图标：像素化方格（8 个小格，深浅交替）."""
        m = 9; cols, rows = 4, 3
        cell = (w - 2 * m) // cols
        for row in range(rows):
            for col in range(cols):
                shade = 160 if (row + col) % 2 == 0 else 255
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(shade, shade, shade))
                x = m + col * cell
                y = m + row * cell
                p.drawRect(x, y, cell, cell)

    def _ic_undo(self, p: QPainter, w: int, h: int):
        """撤销图标：逆时针弧形返回箭头（通用撤销符号）."""
        pen = QPen(self.ICON, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = w // 2, h // 2
        r = 8
        # 逆时针弧线 3/4 圈 (从右下 ~45° 方向逆时针到 ~315°)
        start_angle = 45 * 16
        span_angle = 270 * 16
        p.drawArc(QRect(cx - r, cy - r, r * 2, r * 2), start_angle, span_angle)
        # 箭头尖在弧线起点 (右下角, 表示逆时针回转)
        tip_angle = math.radians(45)
        tip = QPoint(int(cx + r * 1.05 * math.cos(tip_angle)),
                      int(cy + r * 1.05 * math.sin(tip_angle)))
        # 箭头指向左下（逆时针方向）
        arrow_angle = math.radians(45 + 90)  # 垂直弧线朝向圆心
        al = 7
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(self.ICON)
        tri = QPainterPath(); tri.moveTo(tip)
        tri.lineTo(QPoint(int(tip.x() + al * math.cos(arrow_angle + 0.6)),
                          int(tip.y() - al * math.sin(arrow_angle + 0.6))))
        tri.lineTo(QPoint(int(tip.x() + al * math.cos(arrow_angle - 0.6)),
                          int(tip.y() - al * math.sin(arrow_angle - 0.6))))
        tri.closeSubpath(); p.drawPath(tri)

    def _ic_save(self, p: QPainter, w: int, h: int):
        """保存图标：向下箭头 + 下划线（下载/保存通用符号）."""
        pen = QPen(self.ICON, 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        # 顶部短横
        top_y = 9
        p.drawLine(w // 2, top_y, w // 2, h - 14)
        # 向下箭头尖
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(self.ICON)
        tip = QPoint(w // 2, h - 14)
        al = 7
        tri = QPainterPath(); tri.moveTo(tip)
        tri.lineTo(QPoint(tip.x() - al, tip.y() - al))
        tri.lineTo(QPoint(tip.x() + al, tip.y() - al))
        tri.closeSubpath(); p.drawPath(tri)
        # 底部横线（托盘/下划线）
        p.setPen(QPen(self.ICON, 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        bottom_y = h - 8
        p.drawLine(w // 2 - 10, bottom_y, w // 2 + 10, bottom_y)

    def _ic_confirm(self, p: QPainter, w: int, h: int):
        pen = QPen(self.ICON, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin); p.setPen(pen)
        m = 11; mid = w // 2
        p.drawLine(m, h // 2, mid, h - m - 1); p.drawLine(mid, h - m - 1, w - m, m + 2)

    def _ic_cancel(self, p: QPainter, w: int, h: int):
        pen = QPen(self.ICON, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen); m = 13
        p.drawLine(m, m, w - m, h - m); p.drawLine(w - m, m, m, h - m)

    # ═══════════════════════════════════════════════════════
    #  弹出面板
    # ═══════════════════════════════════════════════════════

    def _draw_line_width_popup(self, painter: QPainter):
        p = self.line_width_popup_rect
        # 背景
        path = QPainterPath()
        path.addRoundedRect(p.x(), p.y(), p.width(), p.height(), 6, 6)
        painter.fillPath(path, QColor(50, 50, 50))
        painter.setPen(QPen(QColor(90, 90, 90), 1)); painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(p.x(), p.y(), p.width(), p.height(), 6, 6)

        item_h = 20; gap = 2; pad = 8
        for i, lw in enumerate(LINE_WIDTHS):
            y = p.y() + pad + i * (item_h + gap)
            cx = p.center().x()
            # 高亮当前选中
            if lw == self.line_width:
                hl = QRect(p.x() + 4, y - 1, p.width() - 8, item_h)
                painter.fillRect(hl, QColor(26, 115, 232, 180))
            # 横线
            color = QColor(255, 255, 255) if lw == self.line_width else QColor(200, 200, 200)
            pen = QPen(color, lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(p.x() + 10, y + item_h // 2, p.x() + p.width() - 10, y + item_h // 2)

    def _draw_font_size_popup(self, painter: QPainter):
        p = self.font_size_popup_rect
        path = QPainterPath()
        path.addRoundedRect(p.x(), p.y(), p.width(), p.height(), 6, 6)
        painter.fillPath(path, QColor(50, 50, 50))
        painter.setPen(QPen(QColor(90, 90, 90), 1)); painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(p.x(), p.y(), p.width(), p.height(), 6, 6)

        item_h = 22; gap = 2; pad = 8
        for i, fs in enumerate(FONT_SIZES):
            y = p.y() + pad + i * (item_h + gap)
            # 高亮当前选中
            if fs == self.font_size:
                hl = QRect(p.x() + 4, y - 1, p.width() - 8, item_h)
                painter.fillRect(hl, QColor(26, 115, 232, 180))
            color = QColor(255, 255, 255) if fs == self.font_size else QColor(200, 200, 200)
            painter.setPen(color)
            # 用对应大小的 A 展示
            display_fs = min(fs, 22)
            font = QFont("Microsoft YaHei", display_fs, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(QRect(p.x() + 8, y, p.width() - 16, item_h),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "A")
            # 右侧数字
            font_n = QFont("Microsoft YaHei", 9)
            painter.setFont(font_n)
            painter.drawText(QRect(p.x() + 8, y, p.width() - 16, item_h),
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, str(fs))

    def _draw_tooltip(self, painter: QPainter):
        """在悬停按钮上方绘制文字提示."""
        btn = self._find_btn(self.hovered_action)
        if not btn:
            return
        text = TOOLTIPS.get(self.hovered_action, "")
        if not text:
            return

        font = QFont("Microsoft YaHei", 9)
        painter.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(text) + 8
        th = fm.height() + 4

        cx = btn.rect.center().x()
        x = cx - tw // 2
        y = btn.rect.top() - th - 2

        # 背景
        painter.fillRect(QRect(x, y, tw, th), QColor(60, 60, 60, 230))
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.drawRect(QRect(x, y, tw, th))
        # 文字
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRect(x, y, tw, th), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_color_panel(self, painter: QPainter):
        panel = self.color_panel_rect
        path = QPainterPath()
        path.addRoundedRect(panel.x(), panel.y(), panel.width(), panel.height(), 6, 6)
        painter.fillPath(path, QColor(50, 50, 50))
        painter.setPen(QPen(QColor(90, 90, 90), 1)); painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(panel.x(), panel.y(), panel.width(), panel.height(), 6, 6)

        cs, cg = 22, 6
        for i, (c_hex, _) in enumerate(ANNOTATION_COLORS):
            cx = panel.x() + cg + i * (cs + cg) + cs // 2
            cy = panel.y() + panel.height() // 2
            color = hex_to_qcolor(c_hex)
            painter.setBrush(color)
            painter.setPen(QPen(QColor(140, 140, 140), 1.5) if c_hex.upper() == "#FFFFFF" else Qt.PenStyle.NoPen)
            painter.drawEllipse(cx - cs // 2, cy - cs // 2, cs, cs)
            if c_hex.upper() == self.current_color.upper():
                painter.setPen(QPen(QColor(255, 255, 255), 2.5)); painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(cx - cs // 2 - 4, cy - cs // 2 - 4, cs + 8, cs + 8)
                painter.setPen(QPen(QColor(255, 255, 255), 2.5))
                painter.drawLine(cx - 5, cy, cx - 1, cy + 4); painter.drawLine(cx - 1, cy + 4, cx + 6, cy - 5)


# ─── 自定义光标 ────────────────────────────────────────

def make_crosshair_cursor() -> QCursor:
    """创建一个高可见度的十字光标 (32×32, 蓝白双色)."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    cx, cy = 16, 16
    # 外圈白色描边
    p.setPen(QPen(QColor(255, 255, 255), 4))
    p.drawLine(cx, 1, cx, cy - 3)
    p.drawLine(cx, cy + 3, cx, 31)
    p.drawLine(1, cy, cx - 3, cy)
    p.drawLine(cx + 3, cy, 31, cy)
    # 内圈蓝色
    p.setPen(QPen(QColor(0, 122, 255), 2.5))
    p.drawLine(cx, 1, cx, cy - 3)
    p.drawLine(cx, cy + 3, cx, 31)
    p.drawLine(1, cy, cx - 3, cy)
    p.drawLine(cx + 3, cy, 31, cy)
    # 中心蓝点
    p.setBrush(QColor(0, 122, 255))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(cx - 4, cy - 4, 8, 8)
    p.end()
    return QCursor(pix, 16, 16)
