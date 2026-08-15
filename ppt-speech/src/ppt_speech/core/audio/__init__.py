"""音频处理子包（core 子包）。

整合与音频相关的两类操作，集中暴露音频处理的公共接口：

- **时长解析**（:mod:`ppt_speech.core.audio.duration`）：基于 `tinytag` 读取
  MP3/WAV/M4A/OGG/FLAC 等格式的精确时长。
- **音频嵌入**（:mod:`ppt_speech.core.audio.embedder`）：通过 python-pptx 的
  ``add_movie`` 将 MP3 作为媒体资源嵌入幻灯片，并直接修改底层 OOXML 的时序
  XML，实现幻灯片进入时自动播放。

公共接口
--------
- :func:`get_audio_duration`：读取音频文件播放时长（秒）。
- :func:`embed_audio_autoplay`：将音频嵌入幻灯片并配置进入时自动播放。
- ``P_NS`` / ``P14_NS``：PowerPoint OOXML 主要 / 2010 扩展命名空间常量。
- :func:`_apply_autoplay_timing`：直接修改幻灯片 XML 时序以触发自动播放。

依赖：`tinytag`、`python-pptx`、`lxml`。
"""

from ppt_speech.core.audio.duration import get_audio_duration
from ppt_speech.core.audio.embedder import (
    P14_NS,
    P_NS,
    _apply_autoplay_timing,
    embed_audio_autoplay,
)

__all__ = [
    "P_NS",
    "P14_NS",
    "get_audio_duration",
    "embed_audio_autoplay",
    "_apply_autoplay_timing",
]