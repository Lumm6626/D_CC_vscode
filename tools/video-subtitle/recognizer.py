"""
语音识别模块 - 封装Whisper
"""

import os
import torch
import whisper


def load_model(model_name: str = "base", device: str = "auto"):
    """
    加载Whisper模型

    Args:
        model_name: 模型大小 (tiny/base/small/medium/large)
        device: 设备 (auto/cpu/cuda)

    Returns:
        whisper.Whisper model
    """
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    return whisper.load_model(model_name, device=device)


def extract_audio(video_path: str, output_path: str = None) -> str:
    """
    从视频中提取音频

    Args:
        video_path: 视频文件路径
        output_path: 输出音频路径，默认在视频同目录下创建同名.wav

    Returns:
        str: 音频文件路径
    """
    if output_path is None:
        output_path = os.path.splitext(video_path)[0] + ".wav"

    # 使用ffmpeg提取音频
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        "-y", output_path
    ]

    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"音频提取失败: {result.stderr}")

    return output_path


def transcribe(audio_path: str, model: str = "base", language: str = None) -> dict:
    """
    语音识别，返回 {text, segments: [{start, end, text}]}

    Args:
        audio_path: 音频文件路径
        model: 模型大小 (tiny/base/small/medium/large)
        language: 语言代码，如 "zh", "en", None(自动检测)

    Returns:
        dict: {text: str, segments: list}
    """
    model_instance = load_model(model)

    options = {}
    if language:
        options["language"] = language

    result = model_instance.transcribe(audio_path, **options)

    return {
        "text": result["text"],
        "segments": [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"]
            }
            for seg in result["segments"]
        ]
    }