"""ppt_speech 命令行界面子包。

本包提供 ppt-speech 的命令行入口，包括：
- :func:`main` — 默认配置运行完整配音流程。
- :mod:`ppt_speech.cli.voices` — 刷新可用语音列表。

依赖 core 子包提供的公共功能，不依赖 server 子包。
"""

from ppt_speech.cli.main import main

__all__ = ["main"]