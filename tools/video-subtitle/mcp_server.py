"""
MCP协议入口 - video-subtitle服务
"""

from .server import VideoSubtitleAgent


class VideoSubtitleMCPServer:
    """video-subtitle MCP服务"""

    def __init__(self):
        self.agent = VideoSubtitleAgent()

    def download_and_transcribe(self, url: str, language: str = None) -> dict:
        """
        下载视频并生成字幕

        Args:
            url: 视频URL
            language: 语言代码，如 "zh", "en", None(自动检测)

        Returns:
            dict: 包含 success, subtitle_path, text 等
        """
        return self.agent.download_and_transcribe(url, language)

    def list_subtitles(self, date: str = None) -> list:
        """
        列出字幕文件

        Args:
            date: 可选日期筛选 "YYYY-MM-DD"

        Returns:
            list: 字幕文件列表
        """
        return self.agent.list_outputs(date)

    def download_transcribe_and_proofread(self, url: str, language: str = None) -> dict:
        """
        下载视频、语音识别、文案校对、生成字幕

        Args:
            url: 视频URL
            language: 语言代码，如 "zh", "en", None(自动检测)

        Returns:
            dict: 包含 success, subtitle_path, proofread_subtitle_path, proofread_text 等
        """
        return self.agent.download_transcribe_and_proofread(url, language)

    def get_capabilities(self) -> dict:
        """返回服务能力描述"""
        return {
            "name": "video-subtitle",
            "version": "1.0.0",
            "description": "视频字幕生成服务 - 下载视频、语音识别、生成SRT字幕",
            "methods": [
                "video_subtitle_download_and_transcribe",
                "video_subtitle_download_transcribe_and_proofread",
                "video_subtitle_list"
            ]
        }


# MCP协议处理函数
def handle_video_subtitle_action(action: str, params: dict) -> dict:
    """
    处理MCP请求

    Args:
        action: 操作名称
        params: 参数字典

    Returns:
        dict: 处理结果
    """
    server = VideoSubtitleMCPServer()

    if action == "video_subtitle_download_and_transcribe":
        return server.download_and_transcribe(
            url=params.get("url"),
            language=params.get("language")
        )
    elif action == "video_subtitle_download_transcribe_and_proofread":
        return server.download_transcribe_and_proofread(
            url=params.get("url"),
            language=params.get("language")
        )
    elif action == "video_subtitle_list":
        return {"success": True, "files": server.list_subtitles(params.get("date"))}
    else:
        return {"success": False, "error": f"未知操作: {action}"}