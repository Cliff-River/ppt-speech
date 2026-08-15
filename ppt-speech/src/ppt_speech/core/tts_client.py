"""Edge TTS 客户端模块。

封装与 Microsoft Edge 文本转语音服务的交互逻辑，
包括语音名称标准化、语速验证、TTS 转换及语音列表查询。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from edge_tts import Communicate
from edge_tts.exceptions import (
    EdgeTTSException,
    NoAudioReceived,
    UnexpectedResponse,
    UnknownResponse,
    WebSocketError,
)

_VOICE_PATTERN = re.compile(r"^([a-z]{2,})-([A-Z]{2,})-(.+Neural)$")
_RATE_PATTERN = re.compile(r"^[+-]\d+%$")


def normalize_voice_name(voice_name: str) -> str:
    """将简短语音名称转换为 edge-tts 完整格式。

    短格式示例：'zh-CN-XiaoxiaoNeural'
    完整格式示例：'Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)'

    Args:
        voice_name: 简短语音名称，如 'zh-CN-XiaoxiaoNeural'。
            若输入已是完整格式，则原样返回。

    Returns:
        edge-tts 服务要求的完整语音名称字符串。
    """
    match = _VOICE_PATTERN.match(voice_name)
    if match is None:
        return voice_name

    lang = match.group(1)
    region = match.group(2)
    name = match.group(3)

    # 处理形如 'es-MX-DaliaNeural' 的多段区域名
    if "-" in name:
        region = f"{region}-{name[:name.find('-')]}"
        name = name[name.find("-") + 1:]

    return (
        "Microsoft Server Speech Text to Speech Voice"
        f" ({lang}-{region}, {name})"
    )


async def get_voices_list() -> list[dict[str, Any]]:
    """获取所有可用语音的列表（通过 edge-tts 服务）。

    该列表包含每个语音的名称、语言、性别等元数据，
    用于向用户展示可选的语音方案。

    Returns:
        语音信息字典列表，每项包含 Name、Locale、Gender 等字段。

    Raises:
        EdgeTTSException: 当 TTS 服务返回异常或网络请求失败时。
    """
    from edge_tts import VoicesManager

    try:
        manager = await VoicesManager.create()
    except (UnexpectedResponse, UnknownResponse, WebSocketError) as exc:
        raise EdgeTTSException(f"获取语音列表失败: {exc}") from exc

    voices = manager.voices
    return voices if isinstance(voices, list) else []


async def text_to_mp3(
    text: str,
    save_path: Path,
    voice_name: str = "zh-CN-XiaoxiaoNeural",
    speech_rate: str = "+0%",
) -> bool:
    """使用 edge-tts 将文字转换为 MP3 音频文件。

    该函数会先验证语速格式，然后调用 edge-tts 服务进行合成，
    并将结果保存到指定路径。如果父目录不存在会自动创建。

    Args:
        text: 要转换的文字内容，空白文字将直接返回 False。
        save_path: MP3 文件的保存路径。
        voice_name: 语音名称，如 'zh-CN-XiaoxiaoNeural' 或 'en-US-AriaNeural'。
        speech_rate: 语速调整，格式为 '+0%'、'-50%' 等。

    Returns:
        转换成功返回 True；文字为空或仅含空白字符时返回 False。

    Raises:
        ValueError: 当语速格式不符合 `[+-]数字%` 模式时。
        EdgeTTSException: 当 TTS 服务请求失败（无音频、异常响应、网络错误）时。
        OSError: 当音频文件无法写入（权限、磁盘等）时。
    """
    if not text.strip():
        return False

    if not _RATE_PATTERN.match(speech_rate):
        raise ValueError(f"语速格式错误: '{speech_rate}'，应为 '+0%' 格式")

    full_voice = normalize_voice_name(voice_name)
    communicate = Communicate(text, full_voice, rate=speech_rate)

    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        await communicate.save(str(save_path))
    except (NoAudioReceived, UnexpectedResponse, UnknownResponse, WebSocketError) as exc:
        raise EdgeTTSException(f"TTS 合成失败: {exc}") from exc
    except OSError as exc:
        raise OSError(f"音频文件保存失败 '{save_path}': {exc}") from exc

    return True