"""音频嵌入模块。

负责将 MP3 音频文件嵌入 PowerPoint 幻灯片，并通过修改
底层 XML 配置实现幻灯片进入时音频自动播放。
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree
from pptx.slide import Slide
from pptx.util import Inches

# PowerPoint 主要命名空间 URI
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
# PowerPoint 2010 扩展命名空间 URI（用于媒体元素）
P14_NS = "http://schemas.microsoft.com/office/powerpoint/2010/main"


def _apply_autoplay_timing(slide_element) -> None:
    """修改幻灯片的 XML 时序配置，实现音频自动播放。

    通过以下三处修改确保音频在幻灯片进入时立即播放：
    1. 为媒体元素设置 `playOnEntry` 属性。
    2. 将所有条件延迟归零并添加 `withPrev` 以与进入动画并发。
    3. 为时序树中的媒体节点直接设置 `playOnEntry`。

    Args:
        slide_element: 幻灯片的 lxml 根元素（`slide._element`）。
    """
    # 1. 为 p14:media 元素标记入口自动播放
    for media_el in slide_element.iter(f"{{{P14_NS}}}media"):
        media_el.set(f"{{{P_NS}}}playOnEntry", "1")

    timing = slide_element.find(f"{{{P_NS}}}timing")
    if timing is None:
        return

    # 2. 调整所有条件：零延迟 + withPrev 并发触发
    for cond in timing.findall(f".//{{{P_NS}}}cond"):
        cond.set("delay", "0")
        if cond.find(f"{{{P_NS}}}withPrev") is None:
            etree.SubElement(cond, f"{{{P_NS}}}withPrev")

    # 3. 在媒体节点上再次设置 playOnEntry（兼容不同版本）
    for media_node in timing.findall(f".//{{{P_NS}}}cMediaNode"):
        media_node.set(f"{{{P_NS}}}playOnEntry", "1")


def embed_audio_autoplay(
    slide: Slide,
    audio_path: Path,
    icon_offset: float = -2.0,
    icon_size: float = 1.0,
) -> None:
    """将音频文件嵌入幻灯片并设置为进入时自动播放。

    首先通过 python-pptx 的 `add_movie` 接口将音频作为媒体资源嵌入，
    之后调用 `_apply_autoplay_timing` 直接修改底层 XML 的时序规则，
    让音频在幻灯片进入时自动触发播放。

    图标默认放置在画布边界外（偏移为负英寸），从而在演示时视觉隐藏。

    Args:
        slide: 需要嵌入音频的目标幻灯片对象。
        audio_path: 本地 MP3 音频文件路径。
        icon_offset: 音频图标左上角偏移（英寸），负值表示在画布外隐藏。
        icon_size: 音频图标尺寸（英寸），必须大于 0。

    Raises:
        FileNotFoundError: 当 `audio_path` 指向的文件不存在时。
        ValueError: 当 `icon_size` 小于等于 0 时。
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    if icon_size <= 0:
        raise ValueError(f"图标尺寸必须为正数，当前值: {icon_size}")

    slide.shapes.add_movie(
        str(audio_path),
        left=Inches(icon_offset),
        top=Inches(icon_offset),
        width=Inches(icon_size),
        height=Inches(icon_size),
        poster_frame_image=None,
        mime_type="audio/mpeg",
    )

    _apply_autoplay_timing(slide._element)