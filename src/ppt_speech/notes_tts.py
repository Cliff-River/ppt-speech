"""PPT 备注文字转语音主流程模块。

本模块是 PPT 语音合成功能的顶层入口，负责按顺序编排以下步骤：

1. 验证配置（使用 :mod:`ppt_speech.config`）
2. 打开 PPT 演示文稿
3. 逐页提取备注（使用 :mod:`ppt_speech.notes_reader`）
4. 调用 TTS 服务生成音频（使用 :mod:`ppt_speech.tts_client`）
5. 将音频嵌入幻灯片并配置自动播放（使用 :mod:`ppt_speech.audio_embedder`）
6. 保存输出 PPT 并清理临时文件

其余子模块均保持独立，可单独导入、单独测试，从而实现
低耦合、高内聚的模块化设计。
"""

from __future__ import annotations

import asyncio
import shutil
from typing import Optional

from pptx import Presentation

# 重新导出子模块的公共符号，保持原有 notes_tts 模块的 API 兼容性，
# 这样外部调用方（包括测试）无需修改导入路径即可继续工作。
from ppt_speech.audio_embedder import (
    P14_NS,
    P_NS,
    embed_audio_autoplay,
)
from ppt_speech.config import PTSpeechConfig
from ppt_speech.notes_reader import read_notes_text
from ppt_speech.tts_client import  text_to_mp3

__all__ = [
    "P_NS",
    "P14_NS",
    "PTSpeechConfig",
    "read_notes_text",
    "embed_audio_autoplay",
    "speak_ppt_notes",
    "process_slides",
    "text_to_mp3",
]


async def process_slides(
    prs: Presentation,
    config: PTSpeechConfig,
) -> None:
    """处理演示文稿中的所有幻灯片，生成并嵌入配音。

    按顺序遍历每张幻灯片：
    - 无备注：打印提示并跳过。
    - 有备注：调用 TTS 合成音频，成功后嵌入到幻灯片。
    处理完成后保存输出文件；无论成功与否，都会清理临时音频目录。

    Args:
        prs: python-pptx 已打开的 Presentation 对象。
        config: 配音处理配置对象。

    Raises:
        EdgeTTSException: 当 TTS 合成流程中发生异常时向上抛出。
        OSError: 当输出 PPT 文件无法保存时向上抛出。
    """
    config.temp_audio_dir.mkdir(parents=True, exist_ok=True)

    try:
        for idx, slide in enumerate(prs.slides, start=1):
            note_text = read_notes_text(slide)

            if not note_text:
                print(f"【第{idx}页】无备注，跳过配音")
                continue

            # 打印预览文本（超长截断）以便用户了解处理进度
            preview = note_text[:30] + "..." if len(note_text) > 30 else note_text
            print(f"【第{idx}页】生成语音：{preview}")

            audio_file = config.temp_audio_dir / f"slide_{idx}.mp3"
            success = await text_to_mp3(
                note_text,
                audio_file,
                voice_name=config.voice_name,
                speech_rate=config.speech_rate,
            )

            if success:
                embed_audio_autoplay(
                    slide,
                    audio_file,
                    icon_offset=config.audio_icon_offset,
                    icon_size=config.audio_icon_size,
                )

        config.output_dir.mkdir(parents=True, exist_ok=True)
        prs.save(str(config.output_path))
        print(f"\n✅ 处理完成！输出文件：{config.output_path}")

    finally:
        # 确保临时文件一定被清理
        if config.temp_audio_dir.exists():
            shutil.rmtree(config.temp_audio_dir, ignore_errors=True)


async def speak_ppt_notes(config: Optional[PTSpeechConfig] = None) -> None:
    """PPT 配音处理的顶层入口函数。

    典型用法：

    >>> from ppt_speech import PTSpeechConfig, main
    >>> config = PTSpeechConfig(
    ...     input_dir=Path("data"),
    ...     output_dir=Path("data"),
    ...     voice_name="zh-CN-XiaoxiaoNeural",
    ...     speech_rate="+0%",
    ... )
    >>> asyncio.run(main(config))  # doctest: +SKIP

    Args:
        config: 配音处理配置；若为 None 则使用默认配置。

    Raises:
        ValueError: 当配置参数（语音名称、语速等）不合法时。
        FileNotFoundError: 当输入 PPT 文件不存在时。
        EdgeTTSException: 当 TTS 服务请求失败时。
        OSError: 当文件读写或目录操作失败时。
    """
    if config is None:
        config = PTSpeechConfig()

    config.validate()

    prs = Presentation(str(config.input_path))
    await process_slides(prs, config)


if __name__ == "__main__":
    asyncio.run(speak_ppt_notes())
