"""Edge TTS 客户端模块（向后兼容重导出）。

本模块从 :mod:`ppt_speech.core.tts_client` 重新导出所有公共符号，
以保持 ``from ppt_speech.tts_client import ...`` 可用。
"""

from ppt_speech.core.tts_client import (
    get_voices_list,
    normalize_voice_name,
    text_to_mp3,
)

__all__ = [
    "normalize_voice_name",
    "text_to_mp3",
    "get_voices_list",
]