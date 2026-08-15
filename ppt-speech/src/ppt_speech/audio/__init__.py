"""音频处理子包（向后兼容重导出）。

本模块从 :mod:`ppt_speech.core.audio` 重新导出所有公共符号，
以保持 ``from ppt_speech.audio import ...`` 等既有导入方式可用。
新代码建议直接使用 ``ppt_speech.core.audio``。
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