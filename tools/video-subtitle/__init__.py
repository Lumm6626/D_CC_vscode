"""
video-subtitle - 视频字幕生成工具
支持下载视频、提取音频、语音识别、生成SRT字幕
"""

from .server import VideoSubtitleAgent

__version__ = "1.0.0"
__all__ = ["VideoSubtitleAgent"]