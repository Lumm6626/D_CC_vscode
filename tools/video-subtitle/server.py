"""
视频字幕生成主服务 - VideoSubtitleAgent
协调整个下载→识别→字幕生成流程
"""

import os
import json
from datetime import datetime
from typing import Optional

try:
    from . import downloader, recognizer, subtitle, proofreader
except ImportError:
    import downloader, recognizer, subtitle, proofreader


class VideoSubtitleAgent:
    """视频字幕生成代理"""

    def __init__(self, config_path: str = None):
        """初始化加载配置"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config", "video_subtitle_config.json")

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "downloader": {"output_dir": "video-subtitle/output/downloads"},
                "recognizer": {"model": "base", "model_dir": "video-subtitle/models"},
                "subtitle": {"output_dir": "video-subtitle/output/subtitles"}
            }

    def download_and_transcribe(self, url: str, language: str = None) -> dict:
        """
        下载视频 → 提取音频 → 语音识别 → 生成字幕

        Args:
            url: 视频URL
            language: 语言代码，如 "zh", "en", None(自动检测)

        Returns:
            dict: {success, video_path, audio_path, subtitle_path, text, error}
        """
        download_dir = self.config.get("downloader", {}).get("output_dir", "video-subtitle/output/downloads")
        subtitle_dir = self.config.get("subtitle", {}).get("output_dir", "video-subtitle/output/subtitles")

        # 1. 下载视频
        result = downloader.download_video(url, download_dir)
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "下载失败")}

        video_path = result["video_path"]
        title = result.get("title", "unknown")

        # 2. 提取音频
        audio_path = os.path.splitext(video_path)[0] + ".wav"
        try:
            audio_path = recognizer.extract_audio(video_path, audio_path)
        except Exception as e:
            return {"success": False, "error": f"音频提取失败: {str(e)}"}

        # 3. 语音识别
        model_name = self.config.get("recognizer", {}).get("model", "base")
        try:
            transcribe_result = recognizer.transcribe(audio_path, model=model_name, language=language)
        except Exception as e:
            return {"success": False, "error": f"语音识别失败: {str(e)}"}

        # 4. 生成字幕
        subtitle_filename = f"{title}_{datetime.now().strftime('%Y%m%d%H%M%S')}.srt"
        subtitle_path = os.path.join(subtitle_dir, subtitle_filename)
        try:
            subtitle.generate_srt(transcribe_result["segments"], subtitle_path)
        except Exception as e:
            return {"success": False, "error": f"字幕生成失败: {str(e)}"}

        return {
            "success": True,
            "video_path": video_path,
            "audio_path": audio_path,
            "subtitle_path": subtitle_path,
            "title": title,
            "text": transcribe_result["text"],
            "segments": transcribe_result["segments"]
        }

    def download_transcribe_and_proofread(self, url: str, language: str = None) -> dict:
        """
        下载视频 → 提取音频 → 语音识别 → 文案校对 → 生成字幕（原始+校对双版本）

        Args:
            url: 视频URL
            language: 语言代码，如 "zh", "en", None(自动检测)

        Returns:
            dict: {success, video_path, audio_path, subtitle_path,
                   proofread_subtitle_path, text, proofread_text,
                   proofread_segments, changes_summary, error}
        """
        # Steps 1-3: download, extract audio, transcribe (reuse existing)
        result = self.download_and_transcribe(url, language)
        if not result.get("success"):
            return result

        subtitle_dir = self.config.get("subtitle", {}).get("output_dir", "video-subtitle/output/subtitles")
        title = result.get("title", "unknown")
        text = result.get("text", "")
        segments = result.get("segments", [])

        # Step 4: proofread
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        try:
            proofread_result = proofreader.proofread(text, segments, language)
        except Exception as e:
            return {"success": False, "error": f"文案校对失败: {str(e)}"}

        proofread_text = proofread_result.get("proofread_text", text)
        proofread_segments = proofread_result.get("proofread_segments", segments)
        changes_summary = proofread_result.get("changes_summary", [])

        # Step 5: generate proofread SRT
        proofread_filename = f"{title}_{timestamp}_proofread.srt"
        proofread_subtitle_path = os.path.join(subtitle_dir, proofread_filename)
        try:
            subtitle.generate_srt(proofread_segments, proofread_subtitle_path)
        except Exception as e:
            return {"success": False, "error": f"校对字幕生成失败: {str(e)}"}

        return {
            "success": True,
            "video_path": result.get("video_path"),
            "audio_path": result.get("audio_path"),
            "subtitle_path": result.get("subtitle_path"),
            "proofread_subtitle_path": proofread_subtitle_path,
            "title": title,
            "text": text,
            "proofread_text": proofread_text,
            "proofread_segments": proofread_segments,
            "changes_summary": changes_summary
        }

    def list_outputs(self, date: str = None) -> list:
        """
        列出输出文件

        Args:
            date: 可选日期筛选，格式 "YYYY-MM-DD"

        Returns:
            list: 输出文件列表
        """
        subtitle_dir = self.config.get("subtitle", {}).get("output_dir", "video-subtitle/output/subtitles")

        if not os.path.exists(subtitle_dir):
            return []

        files = []
        for f in os.listdir(subtitle_dir):
            if f.endswith(".srt"):
                full_path = os.path.join(subtitle_dir, f)
                stat = os.stat(full_path)
                mtime = datetime.fromtimestamp(stat.st_mtime)

                if date is None or mtime.strftime("%Y-%m-%d") == date:
                    files.append({
                        "name": f,
                        "path": full_path,
                        "created": mtime.isoformat(),
                        "size": stat.st_size
                    })

        return sorted(files, key=lambda x: x["created"], reverse=True)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        url = sys.argv[1]
        agent = VideoSubtitleAgent()
        result = agent.download_and_transcribe(url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("用法: python server.py <视频URL>")