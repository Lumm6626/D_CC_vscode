"""输出：保存文件、复制剪贴板、打开文件位置."""

import os
from datetime import datetime
from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtGui import QPixmap


def save_to_file(pixmap: QPixmap, parent=None) -> str | None:
    """弹出保存对话框并保存，返回文件路径."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"screenshot_{timestamp}.png"

    filepath, _ = QFileDialog.getSaveFileName(
        parent, "保存截图", default_name,
        "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)"
    )
    if filepath:
        pixmap.save(filepath)
        return filepath
    return None


def copy_to_clipboard(pixmap: QPixmap):
    """复制到剪贴板."""
    QApplication.clipboard().setPixmap(pixmap)


def open_folder(filepath: str):
    """打开文件所在文件夹."""
    import subprocess
    folder = os.path.dirname(os.path.abspath(filepath))
    os.startfile(folder)


def export_and_copy(pixmap: QPixmap, parent=None) -> str | None:
    """保存到临时文件并复制到剪贴板，返回文件路径."""
    temp_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
    os.makedirs(temp_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(temp_dir, f"screenshot_{timestamp}.png")
    pixmap.save(filepath)
    copy_to_clipboard(pixmap)
    return filepath
