"""命令行主入口模块。

提供 ``main()`` 函数作为控制台脚本入口，支持多种参数以自定义
PPT 配音流程。供 ``pyproject.toml`` 中声明的 ``ppt-speech``
控制台脚本调用（``ppt-speech = "ppt_speech.cli:main"``）。
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from ppt_speech.core import PTSpeechConfig, speak_ppt_notes


def _split_path(file_path: str) -> tuple[Path, str]:
    """将文件路径分离为目录和文件名。

    Args:
        file_path: 文件路径字符串，如 ``"data/input.pptx"``。

    Returns:
        ``(目录路径, 文件名)`` 元组。
    """
    p = Path(file_path)
    return p.parent, p.name


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。

    Returns:
        配置完善的 ArgumentParser 实例。
    """
    parser = argparse.ArgumentParser(
        prog="ppt-speech",
        description="PowerPoint 自动配音工具",
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
        help="TTS 语音名称（默认: zh-CN-XiaoxiaoNeural）",
    )
    parser.add_argument(
        "-r", "--rate",
        default="+0%",
        help="语速调整，如 +10%% 或 -5%%（默认: +0%%）",
    )
    parser.add_argument(
        "--auto-advance",
        action="store_true",
        default=True,
        help="启用自动翻页（按音频时长自动设置翻页时间）",
    )
    return parser


def main() -> None:
    """控制台入口：解析参数并运行配音流程。

    供 ``pyproject.toml`` 中声明的 ``ppt-speech`` 控制台脚本调用
    （``ppt-speech = "ppt_speech.cli:main"``），亦可经由
    ``python -m ppt_speech``（见 :mod:`ppt_speech.__main__`）触发。
    """
    parser = build_parser()
    args = parser.parse_args()

    input_dir, input_filename = _split_path(args.input)
    output_dir, output_filename = _split_path(args.output)

    config = PTSpeechConfig(
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