"""多屏截取 + numpy 边缘检测自动吸附."""

import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtCore import QRect


def capture_fullscreen():
    """截取所有屏幕。

    返回 (逻辑分辨率拼接图, luminance数组, 虚拟几何,
           {screen: (geom, DPR-pixmap)}, 物理分辨率拼接图, DPR因子, {screen: DPR}).
    """
    app = QApplication.instance()
    screens = app.screens()

    virtual_geo = app.primaryScreen().virtualGeometry()
    if virtual_geo.isEmpty():
        total_rect = QRect()
        for s in screens:
            total_rect = total_rect.united(s.geometry())
    else:
        total_rect = QRect(virtual_geo)

    # 收集设备像素比
    screen_dprs = {}
    for s in screens:
        screen_dprs[s] = int(s.devicePixelRatio())

    # 每屏截取
    per_screen_logical = {}
    per_screen_physical = {}
    for s in screens:
        geo = s.geometry()
        dpr = screen_dprs[s]
        grab_raw = s.grabWindow(0)                   # 物理像素 + 自带 DPR

        # 逻辑图：保持 DPR，drawPixmap 时 Qt 自动缩放到逻辑坐标
        grab_dpr = QPixmap(grab_raw)
        grab_dpr.setDevicePixelRatio(dpr)
        per_screen_logical[s] = (QRect(geo), grab_dpr)

        # 物理图：去掉 DPR，当纯像素 buffer 用
        grab_phys = QPixmap(grab_raw)
        grab_phys.setDevicePixelRatio(1.0)
        per_screen_physical[s] = (QRect(geo), grab_phys)

    # 逻辑分辨率拼接（UI 使用）
    pixmap = QPixmap(total_rect.size())
    pixmap.fill(0)
    painter = QPainter(pixmap)
    for s, (geo, grab) in per_screen_logical.items():
        offset = geo.topLeft() - total_rect.topLeft()
        painter.drawPixmap(offset, grab)
    painter.end()

    # 物理分辨率拼接（输出使用）：用纯物理像素，不依赖 DPR 缩放
    total_physical_rect = QRect()
    screen_physical_offsets = {}
    for s, (geo, grab) in per_screen_physical.items():
        phys_geo = QRect(geo.topLeft() * screen_dprs[s], grab.size())
        screen_physical_offsets[s] = phys_geo
        total_physical_rect = total_physical_rect.united(phys_geo)

    physical_pixmap = QPixmap(total_physical_rect.size())
    physical_pixmap.fill(0)
    phys_painter = QPainter(physical_pixmap)
    for s, (geo, grab) in per_screen_physical.items():
        offset = screen_physical_offsets[s].topLeft() - total_physical_rect.topLeft()
        phys_painter.drawPixmap(offset, grab)
    phys_painter.end()

    # numpy luminance（用逻辑分辨率图，保持现有 snap 逻辑一致）
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

    return pixmap, luminance, total_rect, per_screen_logical, \
        physical_pixmap, total_physical_rect, screen_dprs


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
