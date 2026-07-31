"""PPT 语音合成包。

将 PowerPoint 幻灯片备注转换为语音并嵌入 PPT 的工具。
"""

from ppt_speech.notes_tts import PTSpeechConfig, speak_ppt_notes

__all__ = ["PTSpeechConfig", "speak_ppt_notes"]