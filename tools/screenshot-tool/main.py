"""入口：QApplication、Windows 原生全局热键、生命周期."""

import sys
import json
import os
import ctypes
from ctypes import wintypes
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PySide6.QtCore import Qt

from capture import capture_fullscreen
from overlay import OverlayManager


def _app_data_dir() -> str:
    """获取用户配置目录 (AppData/Roaming/ScreenshotTool)."""
    base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ScreenshotTool")
    os.makedirs(base, exist_ok=True)
    return base


def _is_frozen() -> bool:
    """判断是否 PyInstaller 打包运行."""
    return getattr(sys, 'frozen', False)


# 配置文件：打包后存在 AppData，开发时存在源码目录
if _is_frozen():
    CONFIG_PATH = os.path.join(_app_data_dir(), "config.json")
else:
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# Win32 API
MOD_CTRL = 0x0002
MOD_ALT = 0x0001
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312

VK_CODES = {
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46, 'g': 0x47,
    'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E,
    'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54, 'u': 0x55,
    'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59, 'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75,
    'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'space': 0x20, 'tab': 0x09, 'enter': 0x0D, 'escape': 0x1B,
    'left': 0x25, 'up': 0x26, 'right': 0x27, 'down': 0x28,
    'print_screen': 0x2C, 'delete': 0x2E, 'insert': 0x2D,
}


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt_x", wintypes.LONG),
        ("pt_y", wintypes.LONG),
    ]


def parse_hotkey(hotkey_str: str) -> tuple[int, int]:
    parts = [p.strip().lower() for p in hotkey_str.split('+')]
    mods = 0
    vk = 0
    for p in parts:
        if p == 'ctrl':
            mods |= MOD_CTRL
        elif p == 'alt':
            mods |= MOD_ALT
        elif p == 'shift':
            mods |= MOD_SHIFT
        elif p == 'win':
            mods |= MOD_WIN
        else:
            vk = VK_CODES.get(p, 0)
    return mods, vk


class HotkeyWidget(QWidget):
    """隐藏窗口，通过 nativeEvent 接收 WM_HOTKEY."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        self.setWindowTitle("screenshot-hotkey")
        self.resize(1, 1)
        # 强制创建原生窗口（不显示）
        self.winId()

    def nativeEvent(self, eventType, message):
        ptr = ctypes.c_void_p(int(message))
        msg = ctypes.cast(ptr, ctypes.POINTER(MSG))
        if msg.contents.message == WM_HOTKEY:
            self._callback()
            return True, 0
        return False, 0


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


class ScreenshotApp:
    HOTKEY_ID = 1

    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.config = load_config()
        self.hotkey = self.config.get("hotkey", "ctrl+alt+a")
        self.overlay_mgr = None
        self._hotkey_ok = False

        self._setup_hotkey()
        self._setup_tray()

        # 启动提示
        if self._hotkey_ok:
            display = self.hotkey.replace('ctrl', 'Ctrl').replace('alt', 'Alt')
            msg = f"截图工具已就绪\n\n快捷键: {display}\n\n也可以右键系统托盘图标操作"
        else:
            msg = "截图工具已就绪\n\n快捷键注册失败，请右键系统托盘图标操作"
        self._tray.showMessage("截图工具", msg, QSystemTrayIcon.MessageIcon.Information, 3000)

    def _setup_hotkey(self):
        try:
            mods, vk = parse_hotkey(self.hotkey)
            if vk == 0:
                print(f"[错误] 无法解析热键: {self.hotkey}")
                return

            self._hotkey_widget = HotkeyWidget(self._do_capture)
            hwnd = int(self._hotkey_widget.winId())

            user32 = ctypes.windll.user32
            ok = user32.RegisterHotKey(hwnd, self.HOTKEY_ID, mods, vk)
            if not ok:
                error = ctypes.get_last_error()
                if error == 1409:
                    print(f"[警告] 快捷键 {self.hotkey} 被其他程序占用，可在 config.json 中修改")
                else:
                    print(f"[警告] 快捷键注册失败 (错误 {error})")
                return

            self._hotkey_ok = True
            display = self.hotkey.replace('ctrl', 'Ctrl').replace('alt', 'Alt')
            print(f"[就绪] 截图工具已启动  |  快捷键: {display}  |  右键托盘退出")

        except Exception as e:
            print(f"[错误] 注册热键异常: {e}")

    def _setup_tray(self):
        self._tray = QSystemTrayIcon()
        # 优先使用 .ico 文件，其次用代码生成的图标
        ico_paths = [
            os.path.join(os.path.dirname(sys.executable), "app.ico"),
            os.path.join(os.path.dirname(__file__), "app.ico"),
        ]
        icon_set = False
        for p in ico_paths:
            if os.path.exists(p):
                self._tray.setIcon(QIcon(p))
                icon_set = True
                break
        if not icon_set:
            pixmap = self._make_tray_pixmap()
            if pixmap:
                self._tray.setIcon(QIcon(pixmap))

        menu = QMenu()
        menu.addAction("截图 (Ctrl+Alt+A)", self._do_capture)
        menu.addSeparator()
        menu.addAction("退出", self._quit)
        self._tray.setContextMenu(menu)
        self._tray.setToolTip(f"截图工具 ({self.hotkey})")

        if self._tray.isSystemTrayAvailable():
            self._tray.show()

    def _make_tray_pixmap(self):
        try:
            pix = QPixmap(32, 32)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor(0, 122, 255), 2)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 122, 255, 60))
            painter.drawRect(4, 4, 24, 18)
            pen.setWidth(3)
            painter.setPen(pen)
            painter.drawLine(4, 8, 4, 4); painter.drawLine(4, 4, 8, 4)
            painter.drawLine(28, 8, 28, 4); painter.drawLine(28, 4, 24, 4)
            painter.drawLine(4, 18, 4, 22); painter.drawLine(4, 22, 8, 22)
            painter.drawLine(28, 18, 28, 22); painter.drawLine(28, 22, 24, 22)
            painter.end()
            return pix
        except Exception:
            return None

    def _do_capture(self):
        if self.overlay_mgr is not None:
            return
        try:
            pixmap, luminance, geometry, per_screen, physical_pixmap, physical_rect, screen_dprs = capture_fullscreen()
            self.overlay_mgr = OverlayManager(pixmap, luminance, geometry, per_screen,
                                              physical_pixmap, physical_rect, screen_dprs)
            self.overlay_mgr.finished.connect(self._on_capture_finished)
        except Exception as e:
            QMessageBox.warning(None, "截图失败", f"截取屏幕失败: {e}")

    def _on_capture_finished(self, result):
        self.overlay_mgr = None

    def _quit(self):
        if hasattr(self, '_hotkey_widget'):
            hwnd = int(self._hotkey_widget.winId())
            ctypes.windll.user32.UnregisterHotKey(hwnd, self.HOTKEY_ID)
        self.app.quit()

    def run(self):
        try:
            sys.exit(self.app.exec())
        except KeyboardInterrupt:
            self._quit()
            sys.exit(0)


def _check_single_instance() -> bool:
    """检查是否已有实例运行，是则弹出提示并返回 False."""
    import ctypes.wintypes
    mutex_name = "Global\\ScreenshotTool_SingleInstance"
    ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(
            0, "截图工具已经在运行中\n\n请查看系统托盘图标或按 Ctrl+Alt+A 开始截图",
            "截图工具", 0x40  # MB_ICONINFORMATION
        )
        return False
    return True


def main():
    if not _check_single_instance():
        return
    ScreenshotApp().run()


if __name__ == "__main__":
    main()
