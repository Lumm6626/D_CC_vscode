"""颜色转换与几何辅助工具."""

from PySide6.QtGui import QColor
from PySide6.QtCore import QRect, QPoint


def hex_to_qcolor(hex_str: str) -> QColor:
    """将 #RRGGBB 或 #RRGGBBAA 字符串转为 QColor."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 6:
        return QColor(f"#{hex_str}")
    elif len(hex_str) == 8:
        r, g, b, a = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16), int(hex_str[6:8], 16)
        return QColor(r, g, b, a)
    return QColor(255, 0, 0)


def qcolor_to_hex(color: QColor) -> str:
    """QColor → #RRGGBB."""
    return f"#{color.red():02X}{color.green():02X}{color.blue():02X}"


def qcolor_to_hex_with_alpha(color: QColor) -> str:
    """QColor → #RRGGBBAA."""
    return f"#{color.red():02X}{color.green():02X}{color.blue():02X}{color.alpha():02X}"


def rect_to_tuple(r: QRect) -> tuple[int, int, int, int]:
    """QRect → (x, y, w, h)."""
    return (r.x(), r.y(), r.width(), r.height())


def normalize_rect(p1: QPoint, p2: QPoint) -> QRect:
    """从任意两个对角点生成 normalized QRect (x/y 为左上角, w/h 为正)."""
    x = min(p1.x(), p2.x())
    y = min(p1.y(), p2.y())
    w = abs(p2.x() - p1.x())
    h = abs(p2.y() - p1.y())
    return QRect(x, y, w, h)


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))
