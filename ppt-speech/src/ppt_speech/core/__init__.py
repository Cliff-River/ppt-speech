"""ppt_speech 核心处理子包。

本包包含 PPT 配音的核心业务逻辑，包括：
- :mod:`ppt_speech.core.config` — 配置数据类与校验逻辑。
- :mod:`ppt_speech.core.notes_reader` — 从幻灯片提取备注文字。
- :mod:`ppt_speech.core.tts_client` — Edge TTS 客户端。
- :mod:`ppt_speech.core.audio` — 音频处理子包（时长解析与嵌入）。
- :mod:`ppt_speech.core.slide_transition` — 设置幻灯片自动翻页时序。
- :mod:`ppt_speech.core.pipeline` — 顶层编排：speak_ppt_notes / process_slides。

依赖关系：core 包不依赖 server 和 cli 子包。
"""

from ppt_speech.core.audio.duration import get_audio_duration
from ppt_speech.core.audio.embedder import embed_audio_autoplay
from ppt_speech.core.config import PTSpeechConfig
from ppt_speech.core.notes_reader import read_notes_text
from ppt_speech.core.pipeline import process_slides, speak_ppt_notes
from ppt_speech.core.slide_transition import set_advance_after_time
from ppt_speech.core.tts_client import (
    get_voices_list,
    normalize_voice_name,
    text_to_mp3,
)

__all__ = [
    "PTSpeechConfig",
    "speak_ppt_notes",
    "process_slides",
    "read_notes_text",
    "set_advance_after_time",
    "text_to_mp3",
    "normalize_voice_name",
    "get_voices_list",
    "embed_audio_autoplay",
    "get_audio_duration",
]