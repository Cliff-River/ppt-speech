"""PPT 配音配置模块。

集中管理 PPT 语音合成的所有配置参数，包括输入输出路径、
语音参数、临时目录设置以及布局参数，并提供配置验证机制。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_RATE_PATTERN = re.compile(r"^[+-]\d+%$")
_VOICE_PATTERN = re.compile(r"^([a-z]{2,})-([A-Z]{2,})-(.+Neural)$")


@dataclass(slots=True)
class PTSpeechConfig:
    """PPT 配音处理配置。

    Attributes:
        input_dir: 输入目录路径，存放原始 PPT 文件。
        output_dir: 输出目录路径，存放生成的配音 PPT 文件。
        input_filename: 输入 PPT 文件名（不含目录路径）。
        output_filename: 输出 PPT 文件名（不含目录路径）。
        voice_name: 语音名称，格式如 'zh-CN-XiaoxiaoNeural'。
        speech_rate: 语速调整，格式如 '+0%' 或 '-50%'。
        temp_audio_dir: 临时音频文件存放目录，处理完成后自动清理。
        audio_icon_offset: 音频图标在画布上的偏移英寸数，负值可实现视觉隐藏。
        audio_icon_size: 音频图标尺寸（英寸）。
    """

    input_dir: Path = field(default_factory=lambda: Path("data"))
    output_dir: Path = field(default_factory=lambda: Path("data"))
    input_filename: str = "input.pptx"
    output_filename: str = "output.pptx"
    voice_name: str = "zh-CN-XiaoxiaoNeural"
    speech_rate: str = "+0%"
    temp_audio_dir: Path = field(default_factory=lambda: Path(".tmp_audio"))
    audio_icon_offset: float = -2.0
    audio_icon_size: float = 1.0

    @property
    def input_path(self) -> Path:
        """完整输入文件路径（input_dir + input_filename）。"""
        return self.input_dir / self.input_filename

    @property
    def output_path(self) -> Path:
        """完整输出文件路径（output_dir + output_filename）。"""
        return self.output_dir / self.output_filename

    def validate(self) -> None:
        """验证配置参数的合法性。

        对语音名称格式、语速格式以及输入文件的存在性进行校验，
        确保后续处理流程不会因为参数错误而中断。

        Raises:
            ValueError: 当语音名称或语速格式不正确时。
            FileNotFoundError: 当输入 PPT 文件不存在时。
        """
        if not _VOICE_PATTERN.match(self.voice_name):
            raise ValueError(
                f"语音名称格式错误: '{self.voice_name}'，"
                f"正确格式如 'zh-CN-XiaoxiaoNeural'"
            )
        if not _RATE_PATTERN.match(self.speech_rate):
            raise ValueError(
                f"语速格式错误: '{self.speech_rate}'，"
                f"正确格式如 '+0%' 或 '-50%'"
            )
        if not self.input_path.exists():
            raise FileNotFoundError(
                f"输入 PPT 文件不存在: {self.input_path}"
            )
