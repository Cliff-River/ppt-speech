"""PPT 配音配置模块。

集中管理 PPT 语音合成的所有配置参数，包括输入输出路径、
语音参数、临时目录设置以及布局参数，并提供配置验证机制。
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import Path

_RATE_PATTERN = re.compile(r"^[+-]\d+%$")
#: 严格语音名称格式：语言-区域-名称（必须以 Neural 结尾）。
_VOICE_PATTERN = re.compile(r"^([a-z]{2,})-([A-Z]{2,})-(.+Neural)$")
#: 宽松的语音名称外形：语言-区域-名称段（允许方言子段，
#: 如 zh-CN-liaoning-XiaobeiNeural），用于在已知语音列表中
#: 区分「格式错误」与「拼写错误导致的语音不存在」。
_VOICE_SHAPE_PATTERN = re.compile(r"^[a-z]{2,}-[A-Z]{2,}(?:-[A-Za-z0-9]+)+$")


def validate_voice_name(
    voice_name: str,
    known_voices: Collection[str] | None = None,
) -> None:
    """校验语音名称的合法性。

    当 ``known_voices`` 为 None 时仅做严格格式校验（不依赖外部数据）；
    当提供已知语音 ShortName 集合时，优先做存在性校验：

    - 名称完全不符合 ``语言-区域-名称`` 外形 → 格式错误；
    - 外形合法但列表中不存在 → 语音不存在，并尽量给出最接近的
      语音名称作为拼写建议（如把 ``...Neura`` 纠正为 ``...Neural``）。

    Args:
        voice_name: 待校验的语音名称，如 ``zh-CN-XiaoxiaoNeural``。
        known_voices: 已知可用的语音 ShortName 集合；为 None 时
            退回纯格式校验。

    Raises:
        ValueError: 语音名称格式错误，或语音在已知列表中不存在。
    """
    if known_voices is None:
        if not _VOICE_PATTERN.match(voice_name):
            raise ValueError(
                f"语音名称格式错误: '{voice_name}'，"
                f"正确格式如 'zh-CN-XiaoxiaoNeural'"
            )
        return

    if voice_name in known_voices:
        return

    if not _VOICE_SHAPE_PATTERN.match(voice_name):
        raise ValueError(
            f"语音名称格式错误: '{voice_name}'，"
            f"正确格式如 'zh-CN-XiaoxiaoNeural'"
        )

    suggestions = difflib.get_close_matches(voice_name, known_voices, n=1)
    hint = f"，你是否想要: '{suggestions[0]}'" if suggestions else ""
    raise ValueError(
        f"语音不存在: '{voice_name}'{hint}，"
        f"可用 `ppt-speech voice` 查询全部可用语音"
    )


@dataclass(slots=True)
class PptSpeechConfig:
    """PPT 配音处理配置。

    Attributes:
        input_dir: 输入目录路径，存放原始 PPT 文件。
        output_dir: 输出目录路径，存放生成的配音 PPT 文件。
        input_filename: 输入 PPT 文件名（不含目录路径）。
        output_filename: 输出 PPT 文件名（不含目录路径）。
        voice_name: 语音名称，格式如 'zh-CN-XiaoxiaoNeural'。
        speech_rate: 语速调整，格式如 '+0%' 或 '-50%'。
        temp_audio_dir: 临时音频文件存放目录；为 None 时使用系统临时目录
            （tempfile）创建，处理完成后自动清理。
        audio_icon_offset: 音频图标在画布上的偏移英寸数，负值可实现视觉隐藏。
        audio_icon_size: 音频图标尺寸（英寸）。
        auto_advance: 是否启用「音频播放完成后自动翻页」功能。
        auto_advance_delay: 自动翻页额外延迟秒数（n），在音频时长基础上增加；
            默认 2.0 秒。
    """

    input_dir: Path = field(default_factory=lambda: Path("data"))
    output_dir: Path = field(default_factory=lambda: Path("data"))
    input_filename: str = "input.pptx"
    output_filename: str = "output.pptx"
    voice_name: str = "zh-CN-XiaoxiaoNeural"
    speech_rate: str = "+0%"
    temp_audio_dir: Path | None = None
    audio_icon_offset: float = -2.0
    audio_icon_size: float = 1.0
    auto_advance: bool = True
    auto_advance_delay: float = 2.0

    @property
    def input_path(self) -> Path:
        """完整输入文件路径（input_dir + input_filename）。"""
        return self.input_dir / self.input_filename

    @property
    def output_path(self) -> Path:
        """完整输出文件路径（output_dir + output_filename）。"""
        return self.output_dir / self.output_filename

    def validate(self, known_voices: Collection[str] | None = None) -> None:
        """验证配置参数的合法性。

        对语音名称、语速格式以及输入文件的存在性进行校验，
        确保后续处理流程不会因为参数错误而中断。

        Args:
            known_voices: 已知可用的语音 ShortName 集合。提供时对
                语音名称做存在性校验（不存在会报「语音不存在」并给出
                拼写建议）；为 None 时仅做格式校验。

        Raises:
            ValueError: 当语音名称/语速格式不正确或语音不存在时。
            FileNotFoundError: 当输入 PPT 文件不存在时。
        """
        validate_voice_name(self.voice_name, known_voices)
        if not _RATE_PATTERN.match(self.speech_rate):
            raise ValueError(
                f"语速格式错误: '{self.speech_rate}'，"
                f"正确格式如 '+0%' 或 '-50%'"
            )
        if not self.input_path.exists():
            raise FileNotFoundError(
                f"输入 PPT 文件不存在: {self.input_path}"
            )
        if self.auto_advance and self.auto_advance_delay < 0:
            raise ValueError(
                f"自动翻页延迟时间不能为负数: {self.auto_advance_delay}"
            )