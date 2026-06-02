"""
视频下载模块 - 封装yt-dlp + 抖音/小红书专用下载路径
"""

import os
import re
import json
import subprocess
from typing import Optional

import requests

# ── 平台检测 ──────────────────────────────────────────────

PLATFORM_PATTERNS = {
    "douyin": [r"douyin\.com", r"v\.douyin\.com", r"iesdouyin\.com"],
    "xiaohongshu": [r"xiaohongshu\.com", r"xhslink\.com"],
}

# ── 环境变量配置 ──────────────────────────────────────────

DOUYIN_API_BASE = os.environ.get("DOUYIN_API_BASE", "http://localhost:8080")
XHS_CDP_URL = os.environ.get("XHS_CDP_URL", "http://127.0.0.1:9222")


def _detect_platform(url: str) -> Optional[str]:
    """根据URL域名检测平台"""
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url):
                return platform
    return None


# ── 抖音：Douyin_TikTok_Download_API 旁路服务 ─────────────

def _download_douyin(url: str, output_dir: str) -> dict:
    """通过 Douyin_TikTok_Download_API 下载抖音视频"""
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Step 1: 解析视频信息
        resp = requests.get(
            f"{DOUYIN_API_BASE}/api/hybrid/video_data",
            params={"url": url, "minimal": "false"},
            timeout=30
        )
        resp.raise_for_status()
        video_data = resp.json()
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": (
                "无法连接抖音 API 旁路服务。请确认：\n"
                "1. Docker 容器已启动: docker run -d --name douyin_api -p 8080:80 evil0ctal/douyin_tiktok_download_api:latest\n"
                "2. DOUYIN_API_BASE 环境变量正确（默认 http://localhost:8080）"
            )
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "抖音 API 请求超时"}
    except Exception as e:
        return {"success": False, "error": f"抖音 API 请求失败: {e}"}

    # Step 2: 提取下载URL和标题
    vd = video_data.get("video_data", {}) if isinstance(video_data, dict) else {}
    download_url = vd.get("nwm_video_url") or vd.get("wm_video_url")
    title = vd.get("title", "unknown")

    if not download_url:
        return {
            "success": False,
            "error": (
                "无法提取视频下载链接，可能原因：\n"
                "1. Cookie 未配置或已过期 — 需在 crawlers/douyin/web/config.yaml 中填入浏览器 Cookie\n"
                "2. 视频链接无效或已删除"
            )
        }

    # Step 3: 下载视频到本地
    try:
        video_bytes = requests.get(download_url, timeout=120).content
    except Exception as e:
        return {"success": False, "error": f"视频下载失败: {e}"}

    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
    video_path = os.path.join(output_dir, f"{safe_title}.mp4")
    with open(video_path, "wb") as f:
        f.write(video_bytes)

    return {"success": True, "video_path": video_path, "title": title, "duration": 0.0}


# ── 小红书：Playwright 浏览器自动化 ────────────────────────

def _download_xiaohongshu(url: str, output_dir: str) -> dict:
    """通过 Playwright 浏览器自动化下载小红书视频"""
    os.makedirs(output_dir, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "success": False,
            "error": "需要安装 Playwright: pip install playwright && playwright install chromium"
        }

    video_url = None
    title = "unknown"

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(XHS_CDP_URL)
            page = browser.new_page()

            # Step 1: 访问链接，等待页面加载
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Step 2: 从 OG 标签提取视频 URL（无水印直链）
            video_url = page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[name="og:video"]');
                    return meta ? meta.getAttribute('content') : null;
                }
            """)

            # Step 3: 提取标题
            title = page.title() or "unknown"

            browser.close()
    except Exception as e:
        error_msg = str(e)
        if "connect" in error_msg.lower() or "ECONNREFUSED" in error_msg.upper():
            return {
                "success": False,
                "error": (
                    "无法连接浏览器调试端口。请确认：\n"
                    '1. 已启动带调试端口的浏览器:\n'
                    '   "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\\xhs-auto"\n'
                    "2. 已在浏览器中登录 xiaohongshu.com\n"
                    f"3. XHS_CDP_URL 环境变量正确（当前: {XHS_CDP_URL}）"
                )
            }
        return {"success": False, "error": f"小红书页面处理失败: {e}"}

    if not video_url:
        return {
            "success": False,
            "error": "无法提取视频链接，可能需要登录或链接已失效"
        }

    # Step 4: 下载视频
    try:
        video_bytes = requests.get(video_url, headers={
            "Referer": "https://www.xiaohongshu.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }, timeout=120).content
    except Exception as e:
        return {"success": False, "error": f"视频下载失败: {e}"}

    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
    video_path = os.path.join(output_dir, f"{safe_title}.mp4")
    with open(video_path, "wb") as f:
        f.write(video_bytes)

    return {"success": True, "video_path": video_path, "title": title, "duration": 0.0}


# ── 通用平台：yt-dlp（现有逻辑） ────────────────────────────

def _download_ytdlp(url: str, output_dir: str) -> dict:
    """通过 yt-dlp 下载视频"""
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        "yt-dlp",
        "--format", "bestvideo+bestaudio/best",
        "--output", os.path.join(output_dir, "%(title)s.%(ext)s"),
        "--no-playlist",
        "--no-check-certificate",
        "--quiet",
        url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or "下载失败"
            }

        # 查找下载的文件
        downloaded_files = []
        for f in os.listdir(output_dir):
            if f.endswith(('.mp4', '.mkv', '.webm', '.flv')):
                downloaded_files.append(f)

        if not downloaded_files:
            return {
                "success": False,
                "error": "未找到下载的文件"
            }

        # 返回最新的文件
        video_path = os.path.join(output_dir, downloaded_files[-1])

        # 获取视频信息
        info_cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            url
        ]
        info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
        info = json.loads(info_result.stdout) if info_result.returncode == 0 else {}

        return {
            "success": True,
            "video_path": video_path,
            "title": info.get("title", "unknown"),
            "duration": info.get("duration", 0.0)
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "下载超时"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── 主入口：平台路由分发 ──────────────────────────────────

def download_video(url: str, output_dir: str, progress_callback: Optional[callable] = None) -> dict:
    """
    下载视频，返回 {success, video_path, title, duration, error}

    根据 URL 自动选择下载策略：
    - 抖音/小红书 → 专用下载路径
    - 其他平台 → yt-dlp

    Args:
        url: 视频URL
        output_dir: 输出目录
        progress_callback: 进度回调函数（仅 yt-dlp 路径可能使用，当前未实现）

    Returns:
        dict: {success: bool, video_path: str, title: str, duration: float, error: str}
    """
    platform = _detect_platform(url)

    if platform == "douyin":
        return _download_douyin(url, output_dir)
    elif platform == "xiaohongshu":
        return _download_xiaohongshu(url, output_dir)
    else:
        return _download_ytdlp(url, output_dir)


def get_video_info(url: str) -> dict:
    """获取视频信息，不下载（仅支持 yt-dlp 兼容平台）"""
    platform = _detect_platform(url)
    if platform:
        return {"platform": platform, "note": "视频信息获取仅支持 yt-dlp 兼容平台"}
    try:
        cmd = ["yt-dlp", "--dump-json", "--no-playlist", url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {}
    except Exception:
        return {}
