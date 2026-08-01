"""可用语音列表刷新工具。

从 Edge TTS 服务拉取全部 Neural 语音并缓存到 ``voices.json``，
供用户挑选 ``voice_name`` 时参考。

用法：

    uv run python -m ppt_speech.voices
"""

from __future__ import annotations

import asyncio
import json

from ppt_speech.tts_client import get_voices_list


async def refresh_voices(output_path: str = "voices.json") -> None:
    """拉取并保存可用语音列表到 JSON 文件。

    Args:
        output_path: 输出 JSON 文件路径，默认为当前目录下的 ``voices.json``。

    Raises:
        EdgeTTSException: 当 TTS 服务请求失败或网络不可用时。
        OSError: 当 JSON 文件无法写入时。
    """
    voices = await get_voices_list()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(voices, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    asyncio.run(refresh_voices())
