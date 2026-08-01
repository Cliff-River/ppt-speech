"""ppt_speech — 将 PowerPoint 备注自动转为语音并嵌入演示文稿的工具包。

功能概述
========
本包读取 ``.pptx`` 文件中每张幻灯片的备注文字，调用 Microsoft Edge 在线
文本转语音（TTS）服务生成 MP3 音频，再将音频嵌入对应幻灯片并修改底层
OOXML 时序，使其在幻灯片进入时自动播放。同时根据每页音频的精确时长，
按「音频时长 + n 秒」设置自动切换时间，实现音频播放完成后自动翻页。
最终输出一份「自带旁白、自动推进」的演示文稿，适合录制网课、自动讲解、
无障碍演示等场景。

模块地图
========
- :mod:`ppt_speech.config` — :class:`PTSpeechConfig` 配置数据类与校验逻辑。
- :mod:`ppt_speech.notes_reader` — 从幻灯片提取备注文字。
- :mod:`ppt_speech.tts_client` — Edge TTS 客户端：合成、语音列表、名称规范化。
- :mod:`ppt_speech.audio` — 音频处理子包：时长解析（tinytag）与音频嵌入。
- :mod:`ppt_speech.slide_transition` — 设置幻灯片自动翻页时序（修改 OOXML advTm）。
- :mod:`ppt_speech.pipeline` — 顶层编排：:func:`speak_ppt_notes` / :func:`process_slides`。
- :mod:`ppt_speech.voices` — 辅助工具：拉取并缓存可用语音列表到 ``voices.json``。

依赖
====
- `edge-tts`：在线 TTS 合成（**无需 API Key**，合成时需联网）。
- `python-pptx`：读写 ``.pptx`` 与操作幻灯片媒体。
- `tinytag`：纯 Python 读取音频时长，支持 MP3/WAV/M4A/OGG/FLAC，无需 ffmpeg。
- `lxml`：直接修改底层 OOXML 时序 XML。

快速使用
========
作为库调用：

>>> import asyncio
>>> from pathlib import Path
>>> from ppt_speech import PTSpeechConfig, speak_ppt_notes
>>> config = PTSpeechConfig(
...     input_dir=Path("data"),
...     output_dir=Path("data"),
...     voice_name="zh-CN-XiaoxiaoNeural",
...     speech_rate="+0%",
... )
>>> asyncio.run(speak_ppt_notes(config))  # doctest: +SKIP

命令行：

- ``uv run ppt-speech``（等价于 ``uv run python -m ppt_speech``）：以默认配置
  运行完整配音流程。
- ``uv run python -m ppt_speech.voices``：刷新可用语音列表到 ``voices.json``。

注意事项
========
- **自动翻页原理**：PowerPoint 原生无「音频结束即翻页」触发器；本包采用
  「读取音频时长 + 缓冲秒数」方案写入 OOXML ``<p:transition>`` 的 ``advTm``
  （毫秒），兼容 PowerPoint 2016/2019/365 与 WPS 演示。可通过
  ``PTSpeechConfig.auto_advance`` 关闭。
- **临时文件**：中间音频默认存于系统临时目录（``tempfile``），处理结束
  （无论成功与否）自动清理；亦可通过 ``PTSpeechConfig.temp_audio_dir`` 指定。
- **优雅降级**：某页音频缺失或时长解析失败时仅跳过该页自动翻页（打印
  ``⚠️`` 警告），不影响整体配音与保存流程。
- 公共 API 统一由本 ``__init__`` 模块导出；子模块亦可单独导入使用。
"""

from ppt_speech.audio import embed_audio_autoplay, get_audio_duration
from ppt_speech.config import PTSpeechConfig
from ppt_speech.notes_reader import read_notes_text
from ppt_speech.pipeline import process_slides, speak_ppt_notes
from ppt_speech.slide_transition import set_advance_after_time
from ppt_speech.tts_client import get_voices_list, normalize_voice_name, text_to_mp3

__all__ = [
    "PTSpeechConfig",
    "speak_ppt_notes",
    "process_slides",
    "get_audio_duration",
    "embed_audio_autoplay",
    "read_notes_text",
    "set_advance_after_time",
    "text_to_mp3",
    "normalize_voice_name",
    "get_voices_list",
    "main",
]


def main() -> None:
    """控制台入口：以默认配置运行完整配音流程。

    供 ``pyproject.toml`` 中声明的 ``ppt-speech`` 控制台脚本调用
    （``ppt-speech = "ppt_speech:main"``），亦可经由
    ``python -m ppt_speech``（见 :mod:`ppt_speech.__main__`）触发。

    当前以 :class:`PTSpeechConfig` 默认值运行（读取 ``data/input.pptx``，
    输出 ``data/output.pptx``）；如需自定义路径、语音或语速，请改用
    :func:`speak_ppt_notes` 显式传入配置对象。
    """
    import asyncio

    asyncio.run(speak_ppt_notes())
