"""PPT 备注文字读取模块。

负责从 PowerPoint 幻灯片中提取备注页中的文字内容，
为后续的语音合成提供输入文本。
"""

from __future__ import annotations

from pptx.slide import Slide


def _read_notes_text(slide: Slide) -> str:
    """从单张幻灯片中提取备注文字。

    检查幻灯片是否具备备注页以及备注文本框，
    然后返回去除首尾空白后的纯文字内容。

    Args:
        slide: python-pptx 的 Slide 对象。

    Returns:
        备注文字内容；若无备注或备注为空则返回空字符串。
    """
    if not slide.has_notes_slide:
        return ""
    notes_slide = slide.notes_slide
    if notes_slide.notes_text_frame is None:
        return ""
    return notes_slide.notes_text_frame.text.strip()
