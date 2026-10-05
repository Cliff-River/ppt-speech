"""``ppt-speech voice`` 子命令实现（音色资源检索）。

提供可用音色（Edge TTS Neural 语音）的列表查询、关键词搜索与
多条件组合过滤（区域、性别、音色类型），并支持本地缓存
``voices.json`` 的读写。本命令仅处理音色资源，不涉及任何 PPT
文件的读取或修改。

用法：

    ppt-speech voice                     # 列出全部音色
    ppt-speech voice xiaoxiao            # 关键词搜索
    ppt-speech voice -l zh -g female     # 区域 + 性别组合过滤
    ppt-speech voice --cache             # 离线读取本地缓存
    ppt-speech voice --refresh           # 联网查询并刷新缓存
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import anyio

from ppt_speech.core.tts_client import get_voices_list

#: 默认本地音色缓存文件路径。
DEFAULT_CACHE_PATH = "voices.json"


async def refresh_voices(output_path: str = DEFAULT_CACHE_PATH) -> list[dict[str, Any]]:
    """拉取全部可用语音并保存到 JSON 缓存文件。

    Args:
        output_path: 输出 JSON 文件路径，默认为当前目录下的 ``voices.json``。

    Returns:
        拉取到的语音信息字典列表。

    Raises:
        EdgeTTSException: 当 TTS 服务请求失败或网络不可用时。
        OSError: 当 JSON 文件无法写入时。
    """
    voices = await get_voices_list()
    async with await anyio.open_file(output_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(voices, ensure_ascii=False, indent=4))
    return voices


def load_voices(cache_path: str = DEFAULT_CACHE_PATH) -> list[dict[str, Any]]:
    """从本地缓存文件读取音色列表。

    Args:
        cache_path: 缓存 JSON 文件路径。

    Returns:
        语音信息字典列表。

    Raises:
        FileNotFoundError: 当缓存文件不存在时。
        json.JSONDecodeError: 当缓存文件不是合法 JSON 时。
    """
    with open(cache_path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _voice_type_text(voice: dict[str, Any]) -> str:
    """提取音色的类型描述（内容类别 + 声音个性）便于类型过滤。"""
    tag = voice.get("VoiceTag") or {}
    categories = tag.get("ContentCategories") or []
    personalities = tag.get("VoicePersonalities") or []
    return " ".join([*categories, *personalities])


def filter_voices(
    voices: list[dict[str, Any]],
    keyword: str | None = None,
    locale: str | None = None,
    gender: str | None = None,
    voice_type: str | None = None,
) -> list[dict[str, Any]]:
    """按多条件组合过滤音色列表，各条件之间为「与」关系。

    Args:
        voices: 原始音色字典列表（Edge TTS 格式）。
        keyword: 关键词，对 ShortName/FriendlyName/Name/Locale 做
            大小写不敏感的子串匹配。
        locale: 语言区域，大小写不敏感，支持前缀匹配（如 ``zh``
            可匹配 ``zh-CN``、``zh-HK``）。
        gender: 性别，``female`` 或 ``male``，大小写不敏感。
        voice_type: 音色类型，对内容类别与声音个性做大小写不敏感的
            子串匹配（如 ``News``、``Sincere``）。

    Returns:
        满足全部给定条件的音色列表（未提供的条件不生效）。
    """
    result: list[dict[str, Any]] = []
    for voice in voices:
        if keyword is not None:
            haystack = " ".join(
                str(voice.get(field, ""))
                for field in ("ShortName", "FriendlyName", "Name", "Locale")
            ).lower()
            if keyword.lower() not in haystack:
                continue
        if locale is not None:
            voice_locale = str(voice.get("Locale", "")).lower()
            if not voice_locale.startswith(locale.lower()):
                continue
        if (gender is not None) and str(voice.get("Gender", "")).lower() != gender.lower():
                continue
        if (voice_type is not None) and voice_type.lower() not in _voice_type_text(voice).lower():
                continue
        result.append(voice)
    return result


def format_voices_table(voices: list[dict[str, Any]]) -> str:
    """将音色列表渲染为对齐的文本表格。

    Args:
        voices: 音色字典列表。

    Returns:
        含表头与每行音色信息的多行字符串（不含末尾换行）。
    """
    name_width = max((len(str(v.get("ShortName", ""))) for v in voices), default=9)
    locale_width = max((len(str(v.get("Locale", ""))) for v in voices), default=4)
    header = (
        f"{'ShortName':<{name_width}} {'性别':<8} "
        f"{'区域':<{locale_width}} 别名"
    )
    lines = [header, "-" * len(header)]
    for voice in voices:
        lines.append(
            f"{voice.get('ShortName', '')!s:<{name_width}} "
            f"{voice.get('Gender', '')!s:<8} "
            f"{voice.get('Locale', '')!s:<{locale_width}} "
            f"{voice.get('FriendlyName', '')!s}"
        )
    return "\n".join(lines)


def register(subparsers: argparse._SubParsersAction) -> None:
    """向子命令解析器注册 ``voice`` 子命令。

    Args:
        subparsers: 顶层解析器的 ``add_subparsers`` 返回值。
    """
    parser = subparsers.add_parser(
        "voice",
        help="检索可用音色列表（不涉及 PPT 文件）",
        description=(
            "查询 Edge TTS 可用音色，支持关键词搜索与多条件组合过滤。"
            "仅处理音色资源，不读取或修改任何 PPT 文件。"
        ),
        epilog=(
            "示例：\n"
            "  ppt-speech voice\n"
            "  ppt-speech voice xiaoxiao\n"
            "  ppt-speech voice -l zh-CN -g female -t News\n"
            "  ppt-speech voice --cache --json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "keyword", nargs="?", default=None,
        help="关键词：对音色名/别名/区域做模糊搜索（可选）",
    )
    parser.add_argument(
        "-l", "--locale", default=None,
        help="按语言区域过滤，支持前缀匹配，如 zh 或 zh-CN",
    )
    parser.add_argument(
        "-g", "--gender", default=None, type=str.lower,
        choices=("female", "male"),
        help="按性别过滤：female 或 male",
    )
    parser.add_argument(
        "-t", "--type", dest="voice_type", default=None,
        help="按音色类型过滤（内容类别或声音个性，如 News、Sincere）",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--cache", action="store_true",
        help=f"离线模式：从本地缓存 {DEFAULT_CACHE_PATH} 读取，不联网",
    )
    source.add_argument(
        "--refresh", action="store_true",
        help=f"联网查询并刷新本地缓存 {DEFAULT_CACHE_PATH}",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="以 JSON 格式输出完整音色元数据",
    )
    parser.set_defaults(handler=run)


async def run(args: argparse.Namespace) -> None:
    """执行音色查询：获取列表 → 组合过滤 → 格式化输出。

    Args:
        args: argparse 解析结果，需包含 ``keyword``、``locale``、
            ``gender``、``voice_type``、``cache``、``refresh``、``json`` 属性。

    Raises:
        EdgeTTSException: 当在线获取音色列表失败时。
        FileNotFoundError: 当离线模式下缓存文件不存在时。
        json.JSONDecodeError: 当缓存文件不是合法 JSON 时。
    """
    if args.cache:
        voices = load_voices()
        source = f"本地缓存 {DEFAULT_CACHE_PATH}"
    else:
        voices = await get_voices_list()
        if args.refresh:
            await refresh_voices()
            source = f"Edge TTS 在线服务（已刷新 {DEFAULT_CACHE_PATH}）"
        else:
            source = "Edge TTS 在线服务"

    filtered = filter_voices(
        voices,
        keyword=args.keyword,
        locale=args.locale,
        gender=args.gender,
        voice_type=args.voice_type,
    )

    if args.json:
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
    elif filtered:
        print(format_voices_table(filtered))
    else:
        print("没有匹配的音色，请调整关键词或过滤条件。")

    print(f"\n共 {len(filtered)} 个音色（总计 {len(voices)} 个，来源: {source}）")


if __name__ == "__main__":
    asyncio.run(refresh_voices())
