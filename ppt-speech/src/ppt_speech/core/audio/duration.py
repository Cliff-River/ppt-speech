"""音频时长解析模块。

使用 tinytag 库读取常见音频格式（MP3、WAV、M4A、OGG、FLAC 等）的
精确时长，供自动翻页功能计算每页幻灯片的停留时间使用。

tinytag 为纯 Python 实现，无需 ffmpeg 等系统级依赖，安装与跨平台使用简便。
"""

from __future__ import annotations

from pathlib import Path

from tinytag import TinyTag


def get_audio_duration(audio_path: Path) -> float:
    """返回音频文件的播放时长（秒）。

    Args:
        audio_path: 音频文件路径，支持 MP3、WAV、M4A、OGG、FLAC 等格式。

    Returns:
        音频时长（秒，浮点数）。

    Raises:
        FileNotFoundError: 当音频文件不存在时。
        ValueError: 当无法解析音频时长时（如文件损坏、格式不支持等）。
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    try:
        tag = TinyTag.get(str(audio_path))
    except Exception as exc:
        raise ValueError(f"无法解析音频文件 '{audio_path}': {exc}") from exc

    if tag is None or tag.duration is None:
        raise ValueError(f"无法获取音频时长: {audio_path}")

    return float(tag.duration)