"""多屏截取 + numpy 边缘检测自动吸附."""

import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtCore import QRect


def capture_fullscreen() -> tuple[QPixmap, np.ndarray, QRect, dict]:
    """截取所有屏幕。返回 (全桌面拼接图, luminance数组, 虚拟几何, {screen: (geom, pixmap)})."""
    app = QApplication.instance()
    screens = app.screens()

    virtual_geo = app.primaryScreen().virtualGeometry()
    if virtual_geo.isEmpty():
        total_rect = QRect()
        for s in screens:
            total_rect = total_rect.united(s.geometry())
    else:
        total_rect = QRect(virtual_geo)

    # 每屏独立截取（不做缩放，保持原始 DPR 像素）
    per_screen = {}
    for s in screens:
        geo = s.geometry()
        grab = s.grabWindow(0)
        # 设置 DPR 以告知 Qt 该 pixmap 的物理像素密度，避免二次缩放
        grab.setDevicePixelRatio(s.devicePixelRatio())
        per_screen[s] = (QRect(geo), grab)

    # 拼接为全桌面图（统一到逻辑坐标）
    pixmap = QPixmap(total_rect.size())
    pixmap.fill(0)
    painter = QPainter(pixmap)
    for s, (geo, grab) in per_screen.items():
        offset = geo.topLeft() - total_rect.topLeft()
        painter.drawPixmap(offset, grab)
    painter.end()

    # numpy luminance
    img = pixmap.toImage()
    w, h = img.width(), img.height()
    raw = img.bits()
    if isinstance(raw, (bytes, memoryview)):
        arr = np.frombuffer(raw, dtype=np.uint32).reshape((h, w))
    else:
        import ctypes
        buf = (ctypes.c_uint32 * (w * h)).from_address(int(raw))
        arr = np.ctypeslib.as_array(buf).reshape((h, w)).copy()
    r = ((arr >> 16) & 0xFF).astype(np.float32)
    g = ((arr >> 8) & 0xFF).astype(np.float32)
    b = (arr & 0xFF).astype(np.float32)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    return pixmap, luminance, total_rect, per_screen


def auto_snap_edges(luminance: np.ndarray, rect: QRect, threshold: float = 30, radius: int = 30) -> QRect:
    h, w = luminance.shape
    x, y, rw, rh = rect.x(), rect.y(), rect.width(), rect.height()
    x2, y2 = x + rw, y + rh
    ol, ot = _snap(luminance, x, y, y2, -1, threshold, radius), _snap(luminance, y, x, x2, -1, threshold, radius)
    o_r, ob = _snap(luminance, x2, y, y2, 1, threshold, radius), _snap(luminance, y2, x, x2, 1, threshold, radius)
    return QRect(x + ol, y + ot, (x2 + o_r) - (x + ol), (y2 + ob) - (y + ot))


def _snap(luminance, scan_pos, r_start, r_end, direction, threshold, radius):
    h, w = luminance.shape
    offsets, step = [], max(1, (r_end - r_start) // 20)
    for sp in range(r_start, r_end, step):
        bv = _sl(luminance, scan_pos, sp, w, h)
        for d in range(2, radius):
            cv = _sl(luminance, scan_pos + d * direction, sp, w, h)
            if cv is not None and abs(cv - bv) > threshold:
                offsets.append((d - 1) * direction); break
        else: offsets.append(0)
    if not offsets: return 0
    offsets.sort(); return offsets[len(offsets) // 2]


def _sl(arr, x, y, w, h):
    return arr[y, x] if 0 <= x < w and 0 <= y < h else None
