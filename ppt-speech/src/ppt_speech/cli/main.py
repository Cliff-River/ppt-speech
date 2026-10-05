"""命令行主入口模块。

提供 ``main()`` 函数作为控制台脚本入口，按子命令分发：

- ``create`` — 读取 PPT 备注，TTS 配音并嵌入音频，输出新 PPT（见
  :mod:`ppt_speech.cli.create`）。
- ``voice`` — 检索可用音色列表，支持关键词搜索与多条件过滤（见
  :mod:`ppt_speech.cli.voices`）。

供 ``pyproject.toml`` 中声明的 ``ppt-speech`` 控制台脚本调用
（``ppt-speech = "ppt_speech.cli:main"``）。

不带任何参数运行（裸调用）时打印顶层帮助，不执行任何配音流程；
旧版平铺式调用（如 ``ppt-speech -i a.pptx -o b.pptx``）未显式指定
子命令时，自动按 ``create`` 处理。
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from edge_tts.exceptions import EdgeTTSException

from ppt_speech.cli import create as create_cmd
from ppt_speech.cli import voices as voices_cmd

#: 顶层支持的子命令集合。
SUBCOMMANDS = ("create", "voice")

#: 视为顶层帮助请求、不做 create 注入的首个参数。
_TOP_HELP_FLAGS = {"-h", "--help"}


def _normalize_argv(argv: list[str]) -> list[str]:
    """把 ``--rate "-10%"`` 这类以 ``-`` 开头的值改写为 ``--rate=-10%``。

    argparse 默认会把以 ``-`` 开头的下一个 token 当作选项而非值，导致
    形如 ``--rate "-10%"`` 的调用报 ``expected one argument`` 错误。这里
    仅对 ``-r`` / ``--rate`` 做等号化改写，让负数语速也能用空格语法传入。
    """
    rate_flags = {"-r", "--rate"}
    result: list[str] = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in rate_flags and i + 1 < len(argv):
            result.append(f"{token}={argv[i + 1]}")
            i += 2
        else:
            result.append(token)
            i += 1
    return result


def _ensure_subcommand(argv: list[str]) -> list[str]:
    """为兼容旧版平铺式调用补全缺失的子命令。

    Args:
        argv: 原始参数列表（不含程序名）。

    Returns:
        补全后的参数列表。空参数（裸调用，由 ``main`` 打印顶层帮助）、
        首个参数已是子命令或为帮助请求时原样返回；否则视为旧版
        ``create`` 用法，在开头注入 ``create``。
    """
    if not argv or argv[0] in SUBCOMMANDS or argv[0] in _TOP_HELP_FLAGS:
        return argv
    return ["create", *argv]


def build_parser() -> argparse.ArgumentParser:
    """构建顶层命令行参数解析器（含子命令）。

    Returns:
        配置完善的 ArgumentParser 实例，子命令处理器挂在
        ``args.handler`` 上。
    """
    parser = argparse.ArgumentParser(
        prog="ppt-speech",
        description="PowerPoint 自动配音工具：读取 PPT 备注生成语音并嵌入幻灯片。",
        epilog=(
            "子命令：\n"
            "  create  读取 PPT，TTS 配音，嵌入音频，输出新 PPT\n"
            "  voice   检索音色列表、关键词搜索音色（不碰 PPT 文件）\n"
            "\n"
            "示例：\n"
            "  ppt-speech create -i data/input.pptx -o data/output.pptx\n"
            "  ppt-speech voice -l zh-CN -g female\n"
            "\n"
            "不带任何参数直接运行 `ppt-speech` 将显示本帮助，不会执行配音；\n"
            "`ppt-speech create` 缺少必填的 -i/-o 时同样只显示 create 帮助。\n"
            "\n"
            "向后兼容：以旧版平铺选项开头（如 -i、-o）时自动按 create\n"
            "处理，如 `ppt-speech -i a.pptx -o b.pptx` 等价于 "
            "`ppt-speech create -i a.pptx -o b.pptx`。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="{create,voice}")
    create_cmd.register(subparsers)
    voices_cmd.register(subparsers)
    return parser


def main() -> None:
    """控制台入口：解析参数并分发到对应子命令。

    供 ``pyproject.toml`` 中声明的 ``ppt-speech`` 控制台脚本调用
    （``ppt-speech = "ppt_speech.cli:main"``），亦可经由
    ``python -m ppt_speech``（见 :mod:`ppt_speech.__main__`）触发。

    Raises:
        SystemExit: 参数错误时以退出码 2 终止；业务错误以 1 终止；
            用户中断（Ctrl+C）以 130 终止。
    """
    parser = build_parser()
    argv = _normalize_argv(_ensure_subcommand(sys.argv[1:]))
    args = parser.parse_args(argv)

    if getattr(args, "handler", None) is None:
        # 未指定任何子命令（如裸调用 `ppt-speech`）时打印顶层帮助。
        parser.print_help()
        return

    if getattr(args, "command", None) == "create" and not (args.input and args.output):
        # `create` 不再提供隐式默认路径：缺少必填的 -i/-o 时打印
        # create 子命令帮助，而不是回退执行 data/input.pptx。
        args.subparser.print_help()
        return

    try:
        result = args.handler(args)
        if asyncio.iscoroutine(result):
            asyncio.run(result)
    except KeyboardInterrupt:
        print("\n已取消。", file=sys.stderr)
        sys.exit(130)
    except (ValueError, FileNotFoundError, EdgeTTSException, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
