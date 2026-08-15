"""音频时长解析模块（向后兼容重导出）。

本模块从 :mod:`ppt_speech.core.audio.duration` 重新导出所有公共符号，
以保持 ``from ppt_speech.audio.duration import get_audio_duration`` 可用。
"""

from ppt_speech.core.audio.duration import get_audio_duration

__all__ = ["get_audio_duration"]