"""可用语音列表刷新工具（向后兼容重导出）。

本模块从 :mod:`ppt_speech.cli.voices` 重新导出所有公共符号，
以保持 ``python -m ppt_speech.voices`` 等入口可用。
"""

from ppt_speech.cli.voices import refresh_voices

__all__ = ["refresh_voices"]

if __name__ == "__main__":
    import asyncio

    asyncio.run(refresh_voices())