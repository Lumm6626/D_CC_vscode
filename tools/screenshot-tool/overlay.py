"""核心：每屏独立遮罩窗口、共享状态机."""

from PySide6.QtCore import Qt, QRect, QPoint, Signal, QObject
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QPixmap,
    QInputMethodEvent,
)
from PySide6.QtWidgets import QWidget, QApplication

from annotations import (
    Annotation, ToolType, AnnotationState, draw_annotation,
)
from toolbar import ToolbarLayout, ToolbarAction, make_crosshair_cursor
from capture import auto_snap_edges
from exporter import save_to_file, copy_to_clipboard, export_and_copy
from utils import normalize_rect, clamp, hex_to_qcolor
import numpy as np


HANDLE_SIZE = 8


class OverlayManager(QObject):
    """管理截图生命周期、共享状态、标注."""

    finished = Signal(object)

    def __init__(self, fullscreen_pixmap: QPixmap, luminance: np.ndarray,
                 total_geometry: QRect, per_screen: dict,
                 physical_pixmap: QPixmap = None, physical_rect: QRect = None,
                 screen_dprs: dict = None):
        super().__init__()
        self.fullscreen_pixmap = fullscreen_pixmap
        self.luminance = luminance
        self.total_geometry = total_geometry
        self.per_screen = per_screen
        self.physical_pixmap = physical_pixmap or QPixmap(fullscreen_pixmap)
        self.physical_rect = physical_rect or QRect(total_geometry)
        self.screen_dprs = screen_dprs or {}

        self.state = AnnotationState.SELECTING
        self.selection_start: QPoint | None = None
        self.selection_end: QPoint | None = None
        self.selection_rect: QRect | None = None
        self.snap_enabled = True

        self.dragging_handle: str | None = None
        self.drag_start_rect: QRect | None = None
        self.drag_start_pos: QPoint | None = None

        self.annotations: list[Annotation] = []
        self.current_tool: ToolbarAction | None = ToolbarAction.RECT
        self.current_color: str = "#FF3B30"
        self.current_line_width: int = 2
        self.font_size: int = 14
        self.mosaic_block_size: int = 8
        self.tool_colors = {ToolbarAction.RECT: "#FF3B30", ToolbarAction.CIRCLE: "#FF3B30",
                            ToolbarAction.TEXT: "#FFCC00", ToolbarAction.ARROW: "#FF3B30"}

        self.drawing_annotation: Annotation | None = None
        self.draw_start: QPoint | None = None

        self.toolbar = ToolbarLayout()
        self.color_panel_visible = False
        self.editing_text: str = ""           # 文字编辑中的文本（无 widget）
        self.editing_text_rect: QRect = QRect()

        self._crosshair_cursor = make_crosshair_cursor()
        self._source_for_mosaic = QPixmap(fullscreen_pixmap)

        # 每屏一个 overlay
        self.overlays: list["ScreenOverlay"] = []
        for s, (geo, grab) in per_screen.items():
            ov = ScreenOverlay(self, geo, grab)
            self.overlays.append(ov)

        QApplication.processEvents()
        for ov in self.overlays:
            ov.raise_()
        if self.overlays:
            self.overlays[-1].activateWindow()
            self.overlays[-1].setFocus()

    # ─── 选区 ────────────────────────────────────────

    def _current_sel(self):
        if self.selection_start and self.selection_end:
            return normalize_rect(self.selection_start, self.selection_end)
        return self.selection_rect

    def refresh_all(self):
        for ov in self.overlays:
            ov.update()

    # ─── 工具栏 ──────────────────────────────────────

    def _update_toolbar(self):
        if self.selection_rect:
            self.toolbar.build(self.selection_rect, self.current_tool,
                               self.current_line_width, self.font_size, self.current_color)
            self.toolbar.color_panel_visible = self.color_panel_visible

    def _update_toolbar_at(self, local_sel: QRect):
        """用本地坐标构建工具栏（避免全局→本地转换的渲染问题）."""
        if self.selection_rect:
            self.toolbar.build(QRect(local_sel), self.current_tool,
                               self.current_line_width, self.font_size, self.current_color)
            self.toolbar.color_panel_visible = self.color_panel_visible

    def _is_text_editing(self) -> bool:
        """是否正在编辑文字."""
        return bool(self.editing_text_rect and not self.editing_text_rect.isEmpty())

    def on_toolbar(self, action):
        if action == ToolbarAction.UNDO:
            if self.annotations: self.annotations.pop()
        elif action == ToolbarAction.CONFIRM: self.finish()
        elif action == ToolbarAction.CANCEL: self.cancel()
        elif action == ToolbarAction.SAVE:
            if self._is_text_editing():
                self.confirm_text()
            result = self._render_result()
            if save_to_file(result, None): self.finish()
        elif action in (ToolbarAction.RECT, ToolbarAction.CIRCLE, ToolbarAction.TEXT,
                        ToolbarAction.MOSAIC, ToolbarAction.ARROW):
            self.current_tool = None if self.current_tool == action else action
            if self.current_tool in self.tool_colors:
                self.current_color = self.tool_colors[self.current_tool]
        self._update_toolbar()

    # ─── 绘图流程 ────────────────────────────────────

    def start_drawing(self, tt: ToolType, pos: QPoint):
        self.state = AnnotationState.DRAWING
        self.draw_start = QPoint(pos)
        c = self.tool_colors.get(self.current_tool, self.current_color)
        self.drawing_annotation = Annotation(
            tool_type=tt, rect=QRect(pos, pos).normalized(), color=c,
            line_width=self.current_line_width, font_size=self.font_size,
            mosaic_block_size=self.mosaic_block_size,
            arrow_start=QPoint(pos), arrow_end=QPoint(pos))

    def update_drawing(self, pos: QPoint):
        if not self.drawing_annotation or not self.draw_start: return
        r = normalize_rect(self.draw_start, pos)
        if self.drawing_annotation.tool_type == ToolType.ARROW:
            self.drawing_annotation.arrow_start = QPoint(self.draw_start)
            self.drawing_annotation.arrow_end = QPoint(pos)
            self.drawing_annotation.rect = QRect(
                min(self.draw_start.x(), pos.x()) - 20, min(self.draw_start.y(), pos.y()) - 20,
                abs(pos.x() - self.draw_start.x()) + 40, abs(pos.y() - self.draw_start.y()) + 40)
        else:
            self.drawing_annotation.rect = r

    def finish_drawing(self, pos: QPoint):
        if not self.drawing_annotation: self.state = AnnotationState.ANNOTATING; return
        if self.draw_start:
            r = normalize_rect(self.draw_start, pos)
            ms = 3 if self.drawing_annotation.tool_type == ToolType.ARROW else 5
            if self.drawing_annotation.tool_type == ToolType.ARROW or (r.width() > ms and r.height() > ms):
                a = self.drawing_annotation
                if a.tool_type != ToolType.ARROW: a.rect = r
                self.annotations.append(a)
        self.drawing_annotation = None; self.draw_start = None
        self.state = AnnotationState.ANNOTATING; self._update_toolbar()

    def _start_text_edit_at(self, pos: QPoint):
        """在点击位置开始文字编辑，无需拖拽框选."""
        self.editing_text = ""
        w = 800
        if self.selection_rect:
            w = max(200, min(800, self.selection_rect.right() - pos.x() - 10))
        self.editing_text_rect = QRect(pos.x(), pos.y(), w, 2000)
        self.refresh_all()

    def confirm_text(self):
        t = self.editing_text.strip()
        if t:
            self.annotations.append(Annotation(
                tool_type=ToolType.TEXT, rect=QRect(self.editing_text_rect),
                color=self.tool_colors.get(ToolbarAction.TEXT, "#FFCC00"),
                text=t, font_size=self.font_size))
        self.editing_text = ""
        self.editing_text_rect = QRect()
        self._update_toolbar(); self.refresh_all()

    def cancel_text(self):
        self.editing_text = ""
        self.editing_text_rect = QRect()
        self._update_toolbar(); self.refresh_all()

    # ─── 手柄 ────────────────────────────────────────

    def do_resize_move(self, gpos: QPoint):
        r = self.drag_start_rect
        if r is None: return
        dx, dy = gpos.x() - self.drag_start_pos.x(), gpos.y() - self.drag_start_pos.y()
        nr = QRect(r); g = self.total_geometry
        h = self.dragging_handle
        if h == 'move':
            nr.moveTo(clamp(r.x() + dx, g.left(), g.right() - r.width()),
                      clamp(r.y() + dy, g.top(), g.bottom() - r.height()))
        else:
            if 'l' in (h or ''): nr.setLeft(clamp(r.left() + dx, g.left(), r.right() - 10))
            elif 'r' in (h or ''): nr.setRight(clamp(r.right() + dx, r.left() + 10, g.right()))
            if 't' in (h or ''): nr.setTop(clamp(r.top() + dy, g.top(), r.bottom() - 10))
            elif 'b' in (h or ''): nr.setBottom(clamp(r.bottom() + dy, r.top() + 10, g.bottom()))
        self.selection_rect = nr

    def hit_handle(self, gpos: QPoint, rect: QRect) -> str | None:
        s = 10; cx, cy = rect.center().x(), rect.center().y()
        pts = {'tl': rect.topLeft(), 'tr': rect.topRight(), 'bl': rect.bottomLeft(),
               'br': rect.bottomRight(), 't': QPoint(cx, rect.top()), 'b': QPoint(cx, rect.bottom()),
               'l': QPoint(rect.left(), cy), 'r': QPoint(rect.right(), cy)}
        for n, pt in pts.items():
            if QRect(pt.x() - s, pt.y() - s, s * 2, s * 2).contains(gpos): return n
        return None

    # ─── 完成 / 取消 ──────────────────────────────────

    def finish(self):
        if self._is_text_editing():
            self.confirm_text()
        result = self._render_result()
        copy_to_clipboard(result); export_and_copy(result)
        self._cleanup(); self.finished.emit(result)

    def cancel(self):
        self._cleanup(); self.finished.emit(None)

    def _cleanup(self):
        for ov in self.overlays: ov.hide(); ov.deleteLater()
        self.overlays.clear()
        QApplication.processEvents()

    def _render_result(self) -> QPixmap:
        rect = self.selection_rect or self.total_geometry
        max_dpr = max(self.screen_dprs.values()) if self.screen_dprs else 1
        phys_origin = self.physical_rect.topLeft()

        # 物理分辨率输出尺寸
        out_w = int(rect.width() * max_dpr)
        out_h = int(rect.height() * max_dpr)
        result = QPixmap(out_w, out_h)
        result.fill(0)
        painter = QPainter(result)

        # 逐屏合成物理像素
        for s, (geo, _logical_grab) in self.per_screen.items():
            if not geo.intersects(rect):
                continue
            dpr = self.screen_dprs.get(s, 1)
            overlap = geo.intersected(rect)

            # 物理图中当前屏幕的起始偏移
            screen_phys_x = geo.x() * dpr - phys_origin.x()
            screen_phys_y = geo.y() * dpr - phys_origin.y()

            # 源区域在物理拼接图中的坐标
            src_x = int((overlap.x() - geo.x()) * dpr + screen_phys_x)
            src_y = int((overlap.y() - geo.y()) * dpr + screen_phys_y)
            src_w = int(overlap.width() * dpr)
            src_h = int(overlap.height() * dpr)

            # 目标区域在输出图中的坐标（统一到 max_dpr）
            dst_x = int((overlap.x() - rect.x()) * max_dpr)
            dst_y = int((overlap.y() - rect.y()) * max_dpr)
            dst_w = int(overlap.width() * max_dpr)
            dst_h = int(overlap.height() * max_dpr)

            portion = self.physical_pixmap.copy(QRect(src_x, src_y, src_w, src_h))
            if dpr != max_dpr:
                portion = portion.scaled(dst_w, dst_h,
                                         Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(dst_x, dst_y, portion)

        painter.end()

        # 标注：缩放到 max_dpr 物理坐标
        ann_painter = QPainter(result)
        ann_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ann_painter.scale(max_dpr, max_dpr)
        ann_painter.translate(-rect.topLeft())

        for ann in self.annotations:
            # 标注坐标是逻辑坐标；painter 的 scale(max_dpr) 自动处理 DPR 转换
            # 马赛克需要逻辑分辨率源图 + 逻辑坐标偏移
            draw_annotation(ann_painter, ann, self._source_for_mosaic,
                            self.total_geometry.topLeft())

        ann_painter.end()
        return result


# ═════════════════════════════════════════════════════════
#  每屏独立 overlay
# ═════════════════════════════════════════════════════════

class ScreenOverlay(QWidget):
    """覆盖单个屏幕的遮罩窗口，使用屏幕原生 DPR 渲染."""

    def __init__(self, mgr: OverlayManager, geo: QRect, grab: QPixmap):
        super().__init__()
        self.mgr = mgr
        self.screen_geo = geo
        self.grab = grab

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(geo)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        self.show()

    # ─── 坐标 ─────────────────────────────────────────

    def to_global(self, local: QPoint) -> QPoint:
        return QPoint(self.screen_geo.x() + local.x(), self.screen_geo.y() + local.y())

    def to_local(self, gr: QRect) -> QRect:
        return QRect(gr.x() - self.screen_geo.x(), gr.y() - self.screen_geo.y(),
                     gr.width(), gr.height())

    # ─── 绘制 ─────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        m = self.mgr; geo = self.screen_geo

        # 背景：本屏截图（DPR 已正确设置，Qt 自动处理缩放）
        p.drawPixmap(0, 0, self.grab)

        sel = m._current_sel()
        if m.state == AnnotationState.SELECTING:
            if sel and not sel.isEmpty():
                self._draw_mask(p, sel)
                self._draw_border(p, self.to_local(sel))
                self._draw_handles(p, self.to_local(sel))
                self._draw_size_label(p, sel)
            else:
                p.fillRect(self.rect(), QColor(0, 0, 0, 128))
        else:
            if m.selection_rect:
                self._draw_mask(p, m.selection_rect)
                local_sel = self.to_local(m.selection_rect)
                self._draw_border(p, local_sel)
                self._draw_handles(p, local_sel)
                p.save()
                p.translate(-self.screen_geo.x(), -self.screen_geo.y())
                p.setClipRect(m.selection_rect)
                for ann in m.annotations:
                    draw_annotation(p, ann, m._source_for_mosaic, m.total_geometry.topLeft())
                if m.drawing_annotation:
                    draw_annotation(p, m.drawing_annotation, m._source_for_mosaic, m.total_geometry.topLeft())
                # 文字编辑预览
                if m._is_text_editing():
                    self._draw_text_edit_preview(p)
                p.restore()
                self._draw_size_label(p, m.selection_rect)
                # 工具栏：在选区所在 overlay 上用本地坐标直接绘制
                sel_center = m.selection_rect.center()
                if self.screen_geo.contains(sel_center):
                    m._update_toolbar_at(local_sel)
                    m.toolbar.render(p)
        p.end()

    def _draw_text_edit_preview(self, p: QPainter):
        m = self.mgr
        r = m.editing_text_rect
        text_color = m.tool_colors.get(ToolbarAction.TEXT, "#FFCC00")
        color = hex_to_qcolor(text_color)
        font = QFont("Microsoft YaHei", m.font_size)

        if m.editing_text:
            p.setFont(font)
            # 阴影
            shadow_color = QColor(0, 0, 0, 180)
            p.setPen(shadow_color)
            p.drawText(r.adjusted(1, 1, 1, 1), Qt.TextFlag.TextWordWrap, m.editing_text)
            # 正文
            p.setPen(color)
            p.drawText(r, Qt.TextFlag.TextWordWrap, m.editing_text)

            # 光标
            fm = p.fontMetrics()
            cursor_x = r.x() + fm.horizontalAdvance(m.editing_text)
            cursor_y = r.y() + fm.ascent()
            if cursor_x < r.right() - 4:
                p.setPen(QPen(color, 2))
                p.drawLine(cursor_x, r.y() + 2, cursor_x, cursor_y + 2)
        else:
            # 占位提示
            p.setFont(font)
            p.setPen(QColor(180, 180, 180))
            p.drawText(r.x(), r.y() + p.fontMetrics().ascent(), "输入文字")

    def _draw_mask(self, p: QPainter, hole: QRect):
        path = QPainterPath(); path.addRect(self.rect()); path.addRect(self.to_local(hole))
        p.fillPath(path, QColor(0, 0, 0, 128))

    def _draw_border(self, p: QPainter, r: QRect):
        p.setPen(QPen(QColor(0, 122, 255), 2)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawRect(r)

    def _draw_handles(self, p: QPainter, r: QRect):
        p.setBrush(QColor(255, 255, 255)); p.setPen(QPen(QColor(0, 122, 255), 1))
        cx, cy, s = r.center().x(), r.center().y(), 4
        for pt in [r.topLeft(), r.topRight(), r.bottomLeft(), r.bottomRight(),
                   QPoint(cx, r.top()), QPoint(cx, r.bottom()),
                   QPoint(r.left(), cy), QPoint(r.right(), cy)]:
            p.drawRect(QRect(pt.x() - s, pt.y() - s, s * 2, s * 2))

    def _draw_size_label(self, p: QPainter, sel: QRect):
        text = f"{sel.width()} x {sel.height()}"
        font = QFont("Microsoft YaHei", 10); p.setFont(font)
        fm = p.fontMetrics(); tw, th = fm.horizontalAdvance(text) + 8, fm.height() + 4
        local = self.to_local(sel)
        lx, ly = local.right() - tw, local.bottom() + 4
        if ly + th > self.height(): ly = local.bottom() - th - 4
        if lx < 0: lx = local.x()
        lb = QRect(lx, ly, tw, th)
        p.fillRect(lb, QColor(0, 0, 0, 180)); p.setPen(QColor(255, 255, 255))
        p.drawText(lb, Qt.AlignmentFlag.AlignCenter, text)

    # ─── 鼠标 ─────────────────────────────────────────

    def mousePressEvent(self, ev):
        loc = ev.position().toPoint()
        g = self.to_global(loc); m = self.mgr
        self.setFocus()
        if m.state == AnnotationState.SELECTING: self._sel_press(g)
        elif m.state == AnnotationState.ANNOTATING: self._ann_press(g, loc)

    def mouseMoveEvent(self, ev):
        loc = ev.position().toPoint()
        g = self.to_global(loc); m = self.mgr
        if m.state == AnnotationState.SELECTING: self._sel_move(g)
        elif m.state == AnnotationState.ANNOTATING: self._ann_move(g, loc)
        elif m.state == AnnotationState.DRAWING: self._draw_move(g)

    def mouseReleaseEvent(self, ev):
        g = self.to_global(ev.position().toPoint()); m = self.mgr
        if m.state == AnnotationState.SELECTING: self._sel_release(g)
        elif m.state == AnnotationState.ANNOTATING: self._ann_release(g)
        elif m.state == AnnotationState.DRAWING: self._draw_release(g)

    # ─── SELECTING ────────────────────────────────────

    def _sel_press(self, g: QPoint):
        m = self.mgr
        if m.selection_rect:
            h = m.hit_handle(g, m.selection_rect)
            if h: m.dragging_handle = h; m.drag_start_rect = QRect(m.selection_rect); m.drag_start_pos = QPoint(g); return
            if m.selection_rect.contains(g): m.dragging_handle = 'move'; m.drag_start_rect = QRect(m.selection_rect); m.drag_start_pos = QPoint(g); return
        m.selection_start = QPoint(g); m.selection_end = QPoint(g); m.selection_rect = None; m.dragging_handle = None
        m.refresh_all()

    def _sel_move(self, g: QPoint):
        m = self.mgr
        if m.dragging_handle and m.drag_start_rect: m.do_resize_move(g); m.refresh_all(); return
        if m.selection_start: m.selection_end = QPoint(g); m.refresh_all()

    def _sel_release(self, g: QPoint):
        m = self.mgr
        if m.dragging_handle: m.dragging_handle = None; m.drag_start_rect = None; m.drag_start_pos = None; m.snap_enabled = False; m.refresh_all(); return
        if m.selection_start:
            raw = normalize_rect(m.selection_start, g)
            if raw.width() > 5 and raw.height() > 5:
                if m.snap_enabled:
                    offset = m.total_geometry.topLeft()
                    snap_rect = QRect(raw.x() - offset.x(), raw.y() - offset.y(),
                                      raw.width(), raw.height())
                    snap_rect = auto_snap_edges(m.luminance, snap_rect)
                    raw = QRect(snap_rect.x() + offset.x(), snap_rect.y() + offset.y(),
                                snap_rect.width(), snap_rect.height())
                m.selection_rect = raw; m.selection_start = None; m.selection_end = None
                m.snap_enabled = False; m.state = AnnotationState.ANNOTATING
                self.setCursor(Qt.CursorShape.ArrowCursor)
            else: m.selection_start = None; m.selection_end = None
            m.refresh_all()

    # ─── ANNOTATING ───────────────────────────────────

    def _ann_press(self, g: QPoint, loc: QPoint):
        m = self.mgr
        # 弹出面板（使用本地坐标，和工具栏一致）
        if m.toolbar.line_width_popup_visible:
            lw = m.toolbar.hit_line_width(loc)
            if lw is not None: m.current_line_width = lw; m.toolbar.line_width_popup_visible = False; m.refresh_all(); return
            if not m.toolbar.line_width_popup_rect.contains(loc): m.toolbar.line_width_popup_visible = False; m.refresh_all()
        if m.toolbar.font_size_popup_visible:
            fs = m.toolbar.hit_font_size(loc)
            if fs is not None: m.font_size = fs; m.toolbar.font_size_popup_visible = False; m.refresh_all(); return
            if not m.toolbar.font_size_popup_rect.contains(loc): m.toolbar.font_size_popup_visible = False; m.refresh_all()
        if m.color_panel_visible:
            c = m.toolbar.hit_color(loc)
            if c is not None:
                m.current_color = c
                if m.current_tool and m.current_tool in m.tool_colors: m.tool_colors[m.current_tool] = c
                m.color_panel_visible = False; m.refresh_all(); return
            if not m.toolbar.color_panel_rect.contains(loc): m.color_panel_visible = False; m.refresh_all()

        # 工具栏按钮（本地坐标）
        act = m.toolbar.hit_test(loc)
        if act is not None:
            if act == ToolbarAction.COLOR:
                m.color_panel_visible = not m.color_panel_visible
                m.toolbar.line_width_popup_visible = m.toolbar.font_size_popup_visible = False
                m.refresh_all(); return
            if act == ToolbarAction.LINE_WIDTH:
                m.toolbar.line_width_popup_visible = not m.toolbar.line_width_popup_visible
                m.toolbar.font_size_popup_visible = m.color_panel_visible = False
                m.refresh_all(); return
            if act == ToolbarAction.FONT_SIZE:
                m.toolbar.font_size_popup_visible = not m.toolbar.font_size_popup_visible
                m.toolbar.line_width_popup_visible = m.color_panel_visible = False
                m.refresh_all(); return
            m.on_toolbar(act)
            m.toolbar.line_width_popup_visible = m.toolbar.font_size_popup_visible = m.color_panel_visible = False
            m.refresh_all(); return

        # 文字编辑中，任意点击先确认文字
        if m._is_text_editing():
            m.confirm_text(); return

        # 手柄 / 选区
        if m.selection_rect:
            h = m.hit_handle(g, m.selection_rect)
            if h: m.dragging_handle = h; m.drag_start_rect = QRect(m.selection_rect); m.drag_start_pos = QPoint(g); return
            if m.selection_rect.contains(g):
                t = m.current_tool
                if t == ToolbarAction.RECT: m.start_drawing(ToolType.RECT, g)
                elif t == ToolbarAction.CIRCLE: m.start_drawing(ToolType.CIRCLE, g)
                elif t == ToolbarAction.TEXT: m._start_text_edit_at(g)
                elif t == ToolbarAction.MOSAIC: m.start_drawing(ToolType.MOSAIC, g)
                elif t == ToolbarAction.ARROW: m.start_drawing(ToolType.ARROW, g)
                else: m.dragging_handle = 'move'; m.drag_start_rect = QRect(m.selection_rect); m.drag_start_pos = QPoint(g)
                m.refresh_all(); return

    def _ann_move(self, g: QPoint, loc: QPoint):
        m = self.mgr
        m.toolbar.set_hovered(loc)
        if m.dragging_handle and m.drag_start_rect: m.do_resize_move(g); m.refresh_all(); return
        if m.selection_rect:
            h = m.hit_handle(g, m.selection_rect)
            cmap = {'tl': Qt.CursorShape.SizeFDiagCursor, 'br': Qt.CursorShape.SizeFDiagCursor,
                    'tr': Qt.CursorShape.SizeBDiagCursor, 'bl': Qt.CursorShape.SizeBDiagCursor,
                    'l': Qt.CursorShape.SizeHorCursor, 'r': Qt.CursorShape.SizeHorCursor,
                    't': Qt.CursorShape.SizeVerCursor, 'b': Qt.CursorShape.SizeVerCursor}
            if h: self.setCursor(cmap.get(h, Qt.CursorShape.ArrowCursor))
            elif m.selection_rect.contains(g):
                if m.current_tool == ToolbarAction.TEXT:
                    self.setCursor(Qt.CursorShape.IBeamCursor)
                elif m.current_tool:
                    self.setCursor(m._crosshair_cursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
            else: self.setCursor(Qt.CursorShape.ArrowCursor)

    def _ann_release(self, g: QPoint):
        m = self.mgr
        if m.dragging_handle: m.dragging_handle = None; m.drag_start_rect = None; m.drag_start_pos = None; m.refresh_all(); return
        if m.state == AnnotationState.DRAWING: m.finish_drawing(g); m.refresh_all()

    # ─── DRAWING ──────────────────────────────────────

    def _draw_move(self, g: QPoint):
        self.mgr.update_drawing(g); self.mgr.refresh_all()

    def _draw_release(self, g: QPoint):
        self.mgr.finish_drawing(g); self.mgr.refresh_all()

    # ─── 键盘 ─────────────────────────────────────────

    def keyPressEvent(self, ev):
        m, k, mod = self.mgr, ev.key(), ev.modifiers()
        if k == Qt.Key.Key_Z and mod == Qt.KeyboardModifier.ControlModifier:
            if m.annotations: m.annotations.pop(); m.refresh_all(); return

        # 文字编辑状态
        if m._is_text_editing():
            if k == Qt.Key.Key_Escape:
                m.cancel_text(); return
            if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                m.confirm_text(); return
            if k == Qt.Key.Key_Backspace:
                m.editing_text = m.editing_text[:-1]
                m.refresh_all(); return
            # 其他可打印字符
            text = ev.text()
            if text and ord(text) >= 0x20 and text != '\x7f':
                m.editing_text += text
                m.refresh_all()
            return

        if k == Qt.Key.Key_Escape:
            if m.state == AnnotationState.DRAWING:
                m.drawing_annotation = None; m.draw_start = None; m.state = AnnotationState.ANNOTATING; m.refresh_all(); return
            m.cancel(); return
        if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if m.state == AnnotationState.SELECTING and m.selection_rect:
                m.state = AnnotationState.ANNOTATING; self.setCursor(Qt.CursorShape.ArrowCursor); m.refresh_all(); return
            if m.state == AnnotationState.ANNOTATING: m.finish(); return
            if m.state == AnnotationState.DRAWING: m.finish_drawing(ev.position().toPoint()); m.refresh_all(); return
            return
        if m.state == AnnotationState.ANNOTATING:
            if k == Qt.Key.Key_BracketLeft: m.current_line_width = max(1, m.current_line_width - 1); m.refresh_all(); return
            if k == Qt.Key.Key_BracketRight: m.current_line_width = min(6, m.current_line_width + 1); m.refresh_all(); return
            tm = {Qt.Key.Key_R: ToolbarAction.RECT, Qt.Key.Key_C: ToolbarAction.CIRCLE,
                  Qt.Key.Key_T: ToolbarAction.TEXT, Qt.Key.Key_M: ToolbarAction.MOSAIC, Qt.Key.Key_A: ToolbarAction.ARROW}
            if k in tm:
                a = tm[k]; m.current_tool = None if m.current_tool == a else a
                if m.current_tool in m.tool_colors: m.current_color = m.tool_colors[m.current_tool]
                m.refresh_all(); return
        super().keyPressEvent(ev)

    # ─── 输入法（中文等） ─────────────────────────────

    def inputMethodEvent(self, ev: QInputMethodEvent):
        m = self.mgr
        if m._is_text_editing():
            if ev.commitString():
                m.editing_text += ev.commitString()
            m.refresh_all()
        ev.accept()

    def inputMethodQuery(self, query):
        """返回输入法需要的信息."""
        if query == Qt.InputMethodQuery.ImEnabled:
            return self.mgr._is_text_editing()
        if query == Qt.InputMethodQuery.ImCursorRectangle:
            # 返回光标位置所在的矩形
            return QRect(10, 10, 2, 20)
        if query == Qt.InputMethodQuery.ImSurroundingText:
            return self.mgr.editing_text
        if query == Qt.InputMethodQuery.ImCursorPosition:
            return len(self.mgr.editing_text)
        return super().inputMethodQuery(query)

    def closeEvent(self, ev):
        super().closeEvent(ev)
