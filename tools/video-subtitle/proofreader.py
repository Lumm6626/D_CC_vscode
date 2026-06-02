"""
文案校对模块 - 使用LLM对Whisper识别文本进行校对
纠正同音字错误、补充标点符号、优化口语表达
"""

import os
import json
import copy
import urllib.request


def _call_claude(text: str, language: str = None) -> dict:
    """使用Anthropic Claude API校对文本"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    lang_name = "中文" if (language and "zh" in language) else "the detected language"

    prompt = f"""你是一位专业的文案校对专家。以下是一段从视频中通过语音识别（Whisper）提取的{lang_name}文本。请进行校对：

1. 纠正同音字、错别字和识别错误
2. 补充适当的标点符号（逗号、句号、问号等）
3. 优化口语表达，使文案更流畅自然
4. 保持原意不变，不要添加或删除实质性内容

请以JSON格式返回结果，不要包含markdown代码块标记：
{{"proofread_text": "校对后的完整文本", "changes": [{{"type": "correction/punctuation/fluency", "original": "原文片段", "corrected": "校对后片段", "reason": "修改原因"}}]}}

原始文本：
{text}"""

    data = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        content = result["content"][0]["text"]
        # Strip markdown code block markers if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        return json.loads(content)


def _call_openai(text: str, language: str = None) -> dict:
    """使用OpenAI API校对文本"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    lang_name = "中文" if (language and "zh" in language) else "the detected language"

    prompt = f"""你是一位专业的文案校对专家。以下是一段从视频中通过语音识别（Whisper）提取的{lang_name}文本。请进行校对：

1. 纠正同音字、错别字和识别错误
2. 补充适当的标点符号（逗号、句号、问号等）
3. 优化口语表达，使文案更流畅自然
4. 保持原意不变，不要添加或删除实质性内容

请以JSON格式返回结果，不要包含markdown代码块标记：
{{"proofread_text": "校对后的完整文本", "changes": [{{"type": "correction/punctuation/fluency", "original": "原文片段", "corrected": "校对后片段", "reason": "修改原因"}}]}}

原始文本：
{text}"""

    data = json.dumps({
        "model": "gpt-4o",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
        return json.loads(content)


def _map_segments(
    segments: list,
    original_text: str,
    proofread_text: str
) -> list:
    """
    将原始segments映射到校对后文本，保持时间戳不变。
    通过字符位置比例映射，在标点边界处切分。
    """
    if not segments or original_text == proofread_text:
        return copy.deepcopy(segments)

    proofread_segments = []
    orig_pos = 0
    proof_pos = 0

    for seg in segments:
        seg_text = seg["text"].strip()
        new_seg = {"start": seg["start"], "end": seg["end"], "text": seg_text}

        # 在原始文本中查找当前segment的位置
        idx = original_text.find(seg_text, orig_pos)

        if idx != -1 and len(proofread_text) > 0:
            # 按比例映射到校对文本
            ratio = idx / max(len(original_text), 1)
            proof_idx = int(ratio * len(proofread_text))

            # 向前查找最近的句子起始边界
            search_start = max(0, proof_idx - 20)
            for sep in ['。', '\n', '！', '？', '.', '!', '?']:
                sep_pos = proofread_text.find(sep, search_start, proof_idx)
                if sep_pos != -1:
                    proof_idx = sep_pos + 1
                    break

            # 估算提取长度（按比例缩放，留余量）
            orig_len = len(seg_text)
            scaled_len = max(orig_len, int(orig_len * len(proofread_text) / max(len(original_text), 1)))
            end_pos = min(proof_idx + scaled_len * 2, len(proofread_text))

            # 在标点或空格处截断
            extracted = proofread_text[proof_idx:end_pos]
            for sep in ['。', '，', '？', '！', '\n', '.', ',', '?', '!', ' ']:
                sep_idx = extracted.find(sep, max(scaled_len // 2, 1))
                if sep_idx != -1:
                    extracted = extracted[:sep_idx + (1 if sep not in (' ', '\n') else 0)]
                    break

            if extracted.strip():
                new_seg["text"] = extracted.strip()

            orig_pos = idx + len(seg_text)
            # proof_pos tracking not strictly needed with the ratio approach

        proofread_segments.append(new_seg)

    return proofread_segments


def proofread(text: str, segments: list, language: str = None) -> dict:
    """
    使用LLM对Whisper识别文本进行校对。

    Args:
        text: Whisper识别的完整文本
        segments: 识别片段列表 [{start, end, text}, ...]
        language: 语言代码，如 "zh", "en", None（自动检测）

    Returns:
        dict: {
            original_text, proofread_text, proofread_segments,
            changes_summary, success, error
        }
    """
    if not text or not text.strip():
        return {
            "original_text": text,
            "proofread_text": text,
            "proofread_segments": segments,
            "changes_summary": [],
            "success": True
        }

    proofread_result = None
    error_msg = None

    # Priority 1: Anthropic Claude
    try:
        proofread_result = _call_claude(text, language)
    except Exception as e:
        error_msg = f"Claude: {e}"

        # Priority 2: OpenAI
        try:
            proofread_result = _call_openai(text, language)
        except Exception as e2:
            error_msg += f"; OpenAI: {e2}"

    # Fallback: return original text
    if proofread_result is None:
        return {
            "original_text": text,
            "proofread_text": text,
            "proofread_segments": copy.deepcopy(segments),
            "changes_summary": [],
            "success": True,
            "error": f"LLM proofreading unavailable, using original text. ({error_msg})"
        }

    proofread_text = proofread_result.get("proofread_text", text)
    changes = proofread_result.get("changes", [])
    proofread_segments = _map_segments(segments, text, proofread_text)

    return {
        "original_text": text,
        "proofread_text": proofread_text,
        "proofread_segments": proofread_segments,
        "changes_summary": changes,
        "success": True
    }
