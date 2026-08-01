"""ppt-speech 服务端示例客户端。

模拟客户端完整流程：上传 pptx → 通过 SSE 实时接收处理进度 → 下载带配音的
结果文件。用于联调测试与使用示例。

依赖（``client`` extra）：``httpx`` + ``httpx-sse``。
安装：``uv pip install -e ".[client]"``。

用法示例
========

    uv run python client.py --server http://127.0.0.1:8000 \
        --input ./data/input.pptx \
        --voice-name zh-CN-XiaoxiaoNeural \
        --auto-advance --output ./out.pptx

退出码：成功 0，失败 1。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx
from httpx_sse.aio import EventSource

_PPTX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ppt-speech 客户端：上传 PPT、接收实时进度、下载结果",
    )
    parser.add_argument(
        "--server",
        default="http://127.0.0.1:8000",
        help="服务端地址（默认 http://127.0.0.1:8000）",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="输入 pptx 文件路径",
    )
    parser.add_argument(
        "--voice-name",
        default="zh-CN-XiaoxiaoNeural",
        help="语音名称（默认 zh-CN-XiaoxiaoNeural）",
    )
    parser.add_argument(
        "--speech-rate",
        default="+0%",
        help="语速（默认 +0%%）",
    )
    parser.add_argument(
        "--auto-advance",
        dest="auto_advance",
        action="store_true",
        default=True,
        help="启用音频结束后自动翻页（默认启用）",
    )
    parser.add_argument(
        "--no-auto-advance",
        dest="auto_advance",
        action="store_false",
        help="禁用自动翻页",
    )
    parser.add_argument(
        "--auto-advance-delay",
        type=float,
        default=2.0,
        help="自动翻页额外延迟秒数（默认 2.0）",
    )
    parser.add_argument(
        "--output",
        default="./output.pptx",
        help="结果文件保存路径（默认 ./output.pptx）",
    )
    return parser.parse_args()


def _format_progress(event_data: dict) -> str:
    """将进度事件格式化为单行可读字符串。"""
    stage = event_data.get("stage", "?")
    idx = event_data.get("slide_idx", 0)
    total = event_data.get("total_slides", 0)
    percent = event_data.get("percent", 0.0)
    eta = event_data.get("eta_seconds")
    message = event_data.get("message", "")
    eta_str = f"ETA {eta}s" if eta is not None else "ETA --"
    if total and idx:
        return (
            f"[{stage}] 第{idx}/{total}页 {percent}% {eta_str} — {message}"
        )
    return f"[{stage}] {percent}% {eta_str} — {message}"


async def _upload(client: httpx.AsyncClient, base: str, args) -> dict:
    """上传文件并返回任务信息。"""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 输入文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "rb") as f:
        files = {"file": (input_path.name, f, _PPTX_MEDIA_TYPE)}
        data = {
            "voice_name": args.voice_name,
            "speech_rate": args.speech_rate,
            "auto_advance": "true" if args.auto_advance else "false",
            "auto_advance_delay": str(args.auto_advance_delay),
        }
        resp = await client.post(
            f"{base}/api/v1/tasks",
            files=files,
            data=data,
            timeout=httpx.Timeout(60.0),
        )

    if resp.status_code != 202:
        print(
            f"❌ 上传失败 ({resp.status_code}): {resp.text}",
            file=sys.stderr,
        )
        sys.exit(1)

    return resp.json()


async def _consume_progress(base: str, progress_url: str) -> bool:
    """订阅 SSE 进度流，返回是否成功完成。"""
    url = f"{base}{progress_url}"
    try:
        async with EventSource(url, timeout=httpx.Timeout(connect=10.0)) as event_source:
            async for event in event_source:
                if not event.data:
                    continue
                import json

                try:
                    data = json.loads(event.data)
                except json.JSONDecodeError:
                    continue

                status = data.get("status", "")
                line = _format_progress(data)
                print(f"\r{line}", end="", flush=True)

                if status == "COMPLETED":
                    print()  # 换行
                    return True
                if status == "FAILED":
                    print()
                    error = data.get("error") or data.get("message", "未知错误")
                    print(f"❌ 处理失败: {error}", file=sys.stderr)
                    return False
    except Exception as exc:
        print(f"\n❌ 进度流异常: {exc}", file=sys.stderr)
        return False
    return False


async def _download(
    client: httpx.AsyncClient, base: str, result_url: str, output: str
) -> bool:
    """下载结果文件。"""
    resp = await client.get(f"{base}{result_url}", timeout=httpx.Timeout(120.0))
    if resp.status_code != 200:
        print(f"❌ 下载失败 ({resp.status_code}): {resp.text}", file=sys.stderr)
        return False

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)
    print(f"✅ 结果已保存: {output_path}")
    return True


async def main_async() -> int:
    args = _parse_args()
    base = args.server.rstrip("/")

    async with httpx.AsyncClient() as client:
        print(f"📤 上传文件: {args.input}")
        task_info = await _upload(client, base, args)
        task_id = task_info["task_id"]
        print(f"✅ 任务已创建: {task_id}")
        print(f"📊 实时进度:")

        success = await _consume_progress(base, task_info["progress_url"])
        if not success:
            return 1

        print(f"📥 下载结果...")
        if not await _download(client, base, task_info["result_url"], args.output):
            return 1
        return 0


def main() -> None:
    sys.exit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
