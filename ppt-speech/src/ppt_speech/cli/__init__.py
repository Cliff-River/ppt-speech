"""ppt_speech 命令行界面子包。

本包提供 ppt-speech 的命令行入口，按子命令组织：
- :func:`main` — 顶层入口，分发到各子命令。
- :mod:`ppt_speech.cli.create` — ``create`` 子命令：读取 PPT 备注，
  TTS 配音并嵌入音频，输出新 PPT。
- :mod:`ppt_speech.cli.voices` — ``voice`` 子命令：检索可用音色列表，
  支持关键词搜索与多条件过滤（不涉及 PPT 文件）。

依赖 core 子包提供的公共功能，不依赖 server 子包。
"""

from ppt_speech.cli.main import main

__all__ = ["main"]