"""音频嵌入模块（向后兼容重导出）。

本模块从 :mod:`ppt_speech.core.audio.embedder` 重新导出所有公共符号，
以保持 ``from ppt_speech.audio.embedder import ...`` 可用。
"""

from ppt_speech.core.audio.embedder import (
    P14_NS,
    P_NS,
    _apply_autoplay_timing,
    embed_audio_autoplay,
)

__all__ = [
    "P_NS",
    "P14_NS",
    "embed_audio_autoplay",
    "_apply_autoplay_timing",
]