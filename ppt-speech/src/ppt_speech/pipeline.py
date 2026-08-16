"""PPT 配音流程编排模块（向后兼容重导出）。

本模块从 :mod:`ppt_speech.core.pipeline` 重新导出所有公共符号，
以保持 ``from ppt_speech.pipeline import ...`` 可用。
同时重新导出 core.pipeline 所依赖的子模块函数，使
``@patch('ppt_speech.pipeline.read_notes_text')`` 等测试路径继续有效。
"""

from ppt_speech.core.audio import embed_audio_autoplay, get_audio_duration
from ppt_speech.core.config import PptSpeechConfig
from ppt_speech.core.notes_reader import read_notes_text
from ppt_speech.core.pipeline import (
    STAGE_COMPLETED,
    STAGE_EMBEDDING,
    STAGE_READING_NOTES,
    STAGE_SAVING,
    STAGE_SETTING_TRANSITION,
    STAGE_SYNTHESIZING,
    STAGE_VALIDATING,
    ProcessProgressEvent,
    ProgressCallback,
    process_slides,
    speak_ppt_notes,
)
from ppt_speech.core.slide_transition import set_advance_after_time
from ppt_speech.core.tts_client import text_to_mp3

__all__ = [
    "STAGE_VALIDATING",
    "STAGE_READING_NOTES",
    "STAGE_SYNTHESIZING",
    "STAGE_EMBEDDING",
    "STAGE_SETTING_TRANSITION",
    "STAGE_SAVING",
    "STAGE_COMPLETED",
    "ProcessProgressEvent",
    "ProgressCallback",
    "PptSpeechConfig",
    "read_notes_text",
    "text_to_mp3",
    "embed_audio_autoplay",
    "get_audio_duration",
    "set_advance_after_time",
    "speak_ppt_notes",
    "process_slides",
]