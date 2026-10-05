"""``ppt-speech create`` 子命令实现。

读取 PPT 每页备注文字，调用 Edge TTS 生成语音，嵌入对应幻灯片，
输出自带旁白与自动翻页的新 PPT 文件。参数与旧版平铺式 CLI 保持
一致（向后兼容）。
"""

from __future__ import annotations

import asyncio
import argparse
from pathlib import Path

from ppt_speech.core import PptSpeechConfig, speak_ppt_notes


def split_path(file_path: str) -> tuple[Path, str]:
    """将文件路径分离为目录和文件名。

    Args:
        file_path: 文件路径字符串，如 ``"data/input.pptx"``。

    Returns:
        ``(目录路径, 文件名)`` 元组。
    """
    p = Path(file_path)
    return p.parent, p.name


def register(subparsers: argparse._SubParsersAction) -> None:
    """向子命令解析器注册 ``create`` 子命令。

    Args:
        subparsers: 顶层解析器的 ``add_subparsers`` 返回值。
    """
    parser = subparsers.add_parser(
        "create",
        help="读取 PPT 备注，TTS 配音并嵌入音频，输出新 PPT",
        description=(
            "读取指定 PPT 文件每页的备注文字，调用 Edge TTS 生成语音，"
            "将音频嵌入对应幻灯片并设置自动翻页，输出新的 PPT 文件。"
        ),
        epilog=(
            "示例：\n"
            "  ppt-speech create -i data/input.pptx -o data/output.pptx\n"
            "  ppt-speech create -v zh-CN-XiaoxiaoNeural -r +10%\n"
            "  ppt-speech create --no-auto-advance"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-i", "--input",
        default="data/input.pptx",
        help="输入 PPT 文件路径（默认: data/input.pptx）",
    )
    parser.add_argument(
        "-o", "--output",
        default="data/output.pptx",
        help="输出 PPT 文件路径（默认: data/output.pptx）",
    )
    parser.add_argument(
        "-v", "--voice",
        default="zh-CN-XiaoxiaoNeural",
        help="TTS 语音名称，可用 `ppt-speech voice` 查询（默认: zh-CN-XiaoxiaoNeural）",
    )
    parser.add_argument(
        "-r", "--rate",
        default="+0%",
        help="语速调整，如 +10%% 或 -5%%（默认: +0%%）",
    )
    parser.add_argument(
        "--auto-advance",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="启用自动翻页（按音频时长自动设置翻页时间），用 --no-auto-advance 关闭（默认启用）",
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace) -> None:
    """执行配音流程：解析路径 → 构建配置 → 运行流水线。

    Args:
        args: argparse 解析结果，需包含 ``input``、``output``、``voice``、
            ``rate``、``auto_advance`` 属性。

    Raises:
        ValueError: 当语音名称或语速格式不正确时。
        FileNotFoundError: 当输入 PPT 文件不存在时。
    """
    input_dir, input_filename = split_path(args.input)
    output_dir, output_filename = split_path(args.output)

    config = PptSpeechConfig(
        input_dir=input_dir,
        input_filename=input_filename,
        output_dir=output_dir,
        output_filename=output_filename,
        voice_name=args.voice,
        speech_rate=args.rate,
        auto_advance=args.auto_advance,
    )
    config.validate()

    asyncio.run(speak_ppt_notes(config))
