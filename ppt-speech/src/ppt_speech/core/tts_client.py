"""Edge TTS 客户端模块。

封装与 Microsoft Edge 文本转语音服务的交互逻辑，
包括语音名称标准化、语速验证、TTS 转换及语音列表查询。

由于 Edge TTS 依赖境外网络，在部分网络环境下连接可能偶发失败，
:func:`text_to_mp3` 内置了指数退避重试，仅对瞬时性错误（协议异常、
网络连接失败、超时）生效；本地磁盘写入等错误不重试。
"""

from __future__ import annotations

import logging
import re
from asyncio import sleep
from pathlib import Path
from typing import Any

import aiohttp
from edge_tts import Communicate
from edge_tts.exceptions import (
    EdgeTTSException,
    UnexpectedResponse,
    UnknownResponse,
    WebSocketError,
)

logger = logging.getLogger(__name__)

_VOICE_PATTERN = re.compile(r"^([a-z]{2,})-([A-Z]{2,})-(.+Neural)$")
_RATE_PATTERN = re.compile(r"^[+-]\d+%$")

#: 默认重试次数（首次尝试之外额外重试的次数）。
DEFAULT_MAX_RETRIES = 3
#: 指数退避基准秒数：第 n 次重试前等待 ``基准 * 2 ** (n - 1)`` 秒。
_RETRY_BASE_DELAY = 1.0
#: 单次退避等待上限秒数，避免重试间隔无限增长。
_RETRY_MAX_DELAY = 8.0

#: 可重试的瞬时性异常。涵盖：
#: - ``EdgeTTSException``：edge-tts 协议层异常（无音频、响应异常、WebSocket 错误、
#:   DRM 时钟偏移等）；
#: - ``aiohttp.ClientError``：连接被拒绝/重置、DNS 解析失败、握手失败、服务端断开等；
#: - ``TimeoutError``：连接或接收超时（含 ``aiohttp.ServerTimeoutError``）；
#: - ``ConnectionError``：底层连接类 ``OSError``（连接重置、中断、管道破裂等）。
_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    EdgeTTSException,
    aiohttp.ClientError,
    TimeoutError,
    ConnectionError,
)


def _retry_delay(retry_index: int) -> float:
    """计算第 ``retry_index`` 次重试前的指数退避等待秒数。

    Args:
        retry_index: 重试序号，从 1 开始（1 表示首次尝试失败后的第一次重试）。

    Returns:
        等待秒数，按 ``2`` 的幂次增长并以 :data:`_RETRY_MAX_DELAY` 封顶。
    """
    return min(_RETRY_BASE_DELAY * 2 ** (retry_index - 1), _RETRY_MAX_DELAY)


def _discard_partial_audio(save_path: Path) -> None:
    """删除失败尝试残留的半成品音频文件。

    ``Communicate.save`` 会在开始流式写入时先以 ``wb`` 打开目标文件，
    因此失败后可能残留空文件或截断文件；重试前清理可避免其被误用。
    清理失败（如文件被占用）不影响重试流程。

    Args:
        save_path: 音频文件路径。
    """
    try:
        save_path.unlink(missing_ok=True)
    except OSError:
        pass


def _patch_edge_tts_endpoint() -> None:
    """将 edge-tts 的合成端点切换到微软 v2 接口。

    微软自 2026-10 起逐步弃用 legacy 合成端点
    ``speech.platform.bing.com``，在多数地区返回 403。
    Edge 155 改用 ``api.msedgeservices.com``，该端点接受
    原有 TrustedClientToken（以 ``Ocp-Apim-Subscription-Key``
    传入）及旧版 Sec-MS-GEC/Version，无需改动 DRM 逻辑。

    由于 ``communicate`` 模块通过 ``from .constants import WSS_URL``
    直接绑定了旧值，必须同时修补两个命名空间才能生效。

    参考：https://github.com/rany2/edge-tts/pull/491
    """
    import edge_tts.communicate as _communicate
    import edge_tts.constants as _constants

    token = _constants.TRUSTED_CLIENT_TOKEN
    new_wss_url = (
        "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
        f"?Ocp-Apim-Subscription-Key={token}"
    )
    _constants.WSS_URL = new_wss_url
    _communicate.WSS_URL = new_wss_url


_patch_edge_tts_endpoint()


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
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> bool:
    """使用 edge-tts 将文字转换为 MP3 音频文件（带指数退避重试）。

    该函数会先验证语速格式，然后调用 edge-tts 服务进行合成，
    并将结果保存到指定路径。如果父目录不存在会自动创建。

    考虑到 Edge TTS 依赖境外网络、国内网络环境下连接可能偶发失败，
    合成失败时会按 ``1s → 2s → 4s → …``（上限 8s）的指数退避自动重试，
    最多额外重试 ``max_retries`` 次。重试仅针对瞬时性错误（协议异常、
    网络连接失败、超时）；本地磁盘写入错误不重试，直接抛出。

    每次重试都是全新的 ``Communicate`` 实例与连接，并会清理上次尝试
    残留的半成品音频文件，因此不会污染最终结果。

    Args:
        text: 要转换的文字内容，空白文字将直接返回 False。
        save_path: MP3 文件的保存路径。
        voice_name: 语音名称，如 'zh-CN-XiaoxiaoNeural' 或 'en-US-AriaNeural'。
        speech_rate: 语速调整，格式为 '+0%'、'-50%' 等。
        max_retries: 首次尝试失败后额外重试的次数；``0`` 表示不重试。

    Returns:
        转换成功返回 True；文字为空或仅含空白字符时返回 False。

    Raises:
        ValueError: 当语速格式不符合 `[+-]数字%` 模式时。
        EdgeTTSException: 当 TTS 服务请求在重试耗尽后仍失败（无音频、
            异常响应、网络错误、超时等）。
        OSError: 当音频文件无法写入（权限、磁盘等）时（不重试）。
    """
    if not text.strip():
        return False

    if not _RATE_PATTERN.match(speech_rate):
        raise ValueError(f"语速格式错误: '{speech_rate}'，应为 '+0%' 格式")

    full_voice = normalize_voice_name(voice_name)
    total_attempts = max(0, max_retries) + 1
    last_error: BaseException | None = None

    for attempt in range(1, total_attempts + 1):
        # 每次尝试都重建 Communicate：其内部 state 与单次连接绑定，
        # 复用旧实例会因 ``stream`` 只能调用一次而失败。
        communicate = Communicate(text, full_voice, rate=speech_rate)
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            await communicate.save(str(save_path))
        except _RETRYABLE_EXCEPTIONS as exc:
            last_error = exc
            # 无论是否继续重试都清理半成品文件，避免留下空/截断的 mp3。
            _discard_partial_audio(save_path)
            if attempt < total_attempts:
                delay = _retry_delay(attempt)
                logger.warning(
                    "TTS 合成第 %d/%d 次尝试失败（%s），%.1fs 后重试",
                    attempt,
                    total_attempts,
                    exc,
                    delay,
                )
                await sleep(delay)
                continue
            logger.error(
                "TTS 合成在 %d 次尝试后仍失败：%s", total_attempts, exc
            )
        except OSError as exc:
            # 走到这里的只剩磁盘/权限等本地错误：与网络无关，重试无意义，
            # 直接失败。（TimeoutError / ConnectionError 属于 OSError 子类，
            # 已由上面的分支先行捕获。）
            raise OSError(f"音频文件保存失败 '{save_path}': {exc}") from exc
        else:
            if attempt > 1:
                logger.info("TTS 合成在第 %d 次尝试成功", attempt)
            return True

    raise EdgeTTSException(
        f"TTS 合成失败（已重试 {total_attempts - 1} 次）: {last_error}"
    )