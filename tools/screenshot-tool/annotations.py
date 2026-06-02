"""标注数据模型 + 渲染（矩形/圆形/文字/马赛克/箭头）."""

from dataclasses import dataclass, field
from enum import Enum, auto
from PySide6.QtCore import QRect, QPoint, Qt, QLineF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QBrush, QPainterPath, QPixmap, QImage, QFontMetrics
from PySide6.QtWidgets import QLineEdit
from utils import hex_to_qcolor


class ToolType(Enum):
    RECT = auto()
    CIRCLE = auto()
    TEXT = auto()
    MOSAIC = auto()
    ARROW = auto()


class AnnotationState(Enum):
    SELECTING = auto()
    ANNOTATING = auto()
    DRAWING = auto()


@dataclass
class Annotation:
    """单个标注的数据模型."""
    tool_type: ToolType
    rect: QRect                          # 标注范围
    color: str = "#FF3B30"               # 颜色 (hex)
    line_width: int = 2                  # 线宽
    text: str = ""                       # 文字内容 (仅 TEXT)
    font_size: int = 14                  # 字号 (仅 TEXT)
    mosaic_block_size: int = 8           # 马赛克块大小 (仅 MOSAIC)
    arrow_start: QPoint = field(default_factory=QPoint)  # 箭头起点 (仅 ARROW)
    arrow_end: QPoint = field(default_factory=QPoint)    # 箭头终点 (仅 ARROW)

    def clone(self) -> "Annotation":
        return Annotation(
            tool_type=self.tool_type,
            rect=QRect(self.rect),
            color=self.color,
            line_width=self.line_width,
            text=self.text,
            font_size=self.font_size,
            mosaic_block_size=self.mosaic_block_size,
            arrow_start=QPoint(self.arrow_start),
            arrow_end=QPoint(self.arrow_end),
        )


def draw_annotation(painter: QPainter, ann: Annotation, source_pixmap: QPixmap | None = None):
    """在 painter 上绘制一个标注."""
    color = hex_to_qcolor(ann.color)

    if ann.tool_type == ToolType.RECT:
        pen = QPen(color, ann.line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(ann.rect)

    elif ann.tool_type == ToolType.CIRCLE:
        pen = QPen(color, ann.line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(ann.rect)

    elif ann.tool_type == ToolType.TEXT:
        if not ann.text:
            # 拖拽中：虚线框预览
            pen = QPen(color, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(ann.rect)
        else:
            # 底部色条
            bar_height = 4
            bar_rect = QRect(ann.rect.x(), ann.rect.bottom() - bar_height, ann.rect.width(), bar_height)
            painter.fillRect(bar_rect, color)
            # 白色文字
            font = QFont("Microsoft YaHei", ann.font_size)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(ann.rect.adjusted(2, 2, -2, -bar_height - 2),
                             Qt.TextFlag.TextSingleLine | Qt.TextFlag.TextWordWrap, ann.text)

    elif ann.tool_type == ToolType.MOSAIC:
        if source_pixmap and not ann.rect.isEmpty():
            _draw_mosaic(painter, source_pixmap, ann.rect, ann.mosaic_block_size)

    elif ann.tool_type == ToolType.ARROW:
        pen = QPen(color, ann.line_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(color)
        _draw_arrow(painter, ann.arrow_start, ann.arrow_end, ann.line_width)


def _draw_mosaic(painter: QPainter, source: QPixmap, rect: QRect, block_size: int = 8):
    """绘制马赛克效果——对区域做 downsample + nearest-neighbor upsample."""
    if rect.width() <= 0 or rect.height() <= 0:
        return
    crop = source.copy(rect)
    small_w = max(1, rect.width() // block_size)
    small_h = max(1, rect.height() // block_size)
    small = crop.scaled(small_w, small_h, Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
    mosaic = small.scaled(rect.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                          Qt.TransformationMode.FastTransformation)
    painter.drawPixmap(rect.topLeft(), mosaic)


def _draw_arrow(painter: QPainter, start: QPoint, end: QPoint, line_width: int):
    """画箭头：线段 + 箭头三角形."""
    painter.drawLine(start, end)

    # 箭头三角
    line = QLineF(start, end)
    angle = line.angle()  # 线的角度
    arrow_len = max(12, line_width * 4)

    import math
    rad = math.radians(angle)
    tip = QPoint(end)

    left_rad = math.radians(angle + 150)
    left_pt = QPoint(int(tip.x() + arrow_len * math.cos(left_rad)),
                     int(tip.y() - arrow_len * math.sin(left_rad)))

    right_rad = math.radians(angle - 150)
    right_pt = QPoint(int(tip.x() + arrow_len * math.cos(right_rad)),
                      int(tip.y() - arrow_len * math.sin(right_rad)))

    path = QPainterPath()
    path.moveTo(tip)
    path.lineTo(left_pt)
    path.lineTo(right_pt)
    path.closeSubpath()
    painter.drawPath(path)
