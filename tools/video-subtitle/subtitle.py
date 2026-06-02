"""
字幕生成模块 - 生成SRT格式
"""

import os


def seconds_to_timestamp(seconds: float) -> str:
    """
    将秒数转换为SRT时间戳格式

    Args:
        seconds: 秒数，如 0.0

    Returns:
        str: 时间戳格式，如 "00:00:00,000"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments: list, output_path: str) -> str:
    """
    将识别结果转为SRT格式

    Args:
        segments: 识别片段列表 [{start, end, text}, ...]
        output_path: 输出SRT文件路径

    Returns:
        str: SRT文件路径
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    srt_content = []
    for i, segment in enumerate(segments, 1):
        start_time = seconds_to_timestamp(segment["start"])
        end_time = seconds_to_timestamp(segment["end"])
        text = segment["text"].strip()

        srt_content.append(f"{i}")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(text)
        srt_content.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_content))

    return output_path