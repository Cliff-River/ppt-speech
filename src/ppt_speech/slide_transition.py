"""幻灯片自动切换（翻页）控制模块。

通过修改幻灯片底层 OOXML 的 ``<p:transition>`` 元素，设置 ``advTm``
（自动前进时间，毫秒）属性，实现幻灯片在指定时间后自动翻页。

这是 PowerPoint 原生的「切换 → 计时 → 在 X 秒后」机制，
兼容 PowerPoint 2016/2019/365，无需宏或运行时自动化。

.. note::

    按 CT_Slide 的 schema 顺序，``<p:transition>`` 必须位于
    ``<p:cSld>`` / ``<p:clrMapOvr>`` 之后、``<p:timing>`` / ``<p:extLst>``
    之前。本模块在新增元素时严格遵守该顺序，以免 PowerPoint 触发文件修复。
"""

from __future__ import annotations

from lxml import etree
from pptx.slide import Slide

from ppt_speech.audio import P_NS


def set_advance_after_time(slide: Slide, delay_seconds: float) -> None:
    """设置幻灯片在指定秒数后自动翻页。

    在 ``<p:transition>`` 元素上写入 ``advTm``（毫秒）。若幻灯片已有
    切换设置（含切换效果），仅更新 ``advTm``，保留原有效果；否则按
    schema 顺序新建 ``<p:transition>`` 元素。

    Args:
        slide: 目标幻灯片对象。
        delay_seconds: 自动翻页延迟时间（秒）。允许为 0，但不能为负数。

    Raises:
        ValueError: 当 ``delay_seconds`` 为负数时。
    """
    if delay_seconds < 0:
        raise ValueError(f"自动翻页延迟时间不能为负数: {delay_seconds}")

    delay_ms = int(round(delay_seconds * 1000))
    _set_adv_tm(slide._element, delay_ms)


def _set_adv_tm(slide_element, delay_ms: int) -> None:
    """在幻灯片根元素上设置/更新 ``advTm`` 属性（毫秒）。

    Args:
        slide_element: 幻灯片的 lxml 根元素（``slide._element``）。
        delay_ms: 自动前进时间（毫秒）。
    """
    transition = slide_element.find(f"{{{P_NS}}}transition")

    if transition is None:
        transition = etree.Element(f"{{{P_NS}}}transition")
        # 按 CT_Slide schema 顺序插入：位于 p:timing / p:extLst 之前。
        anchor = slide_element.find(f"{{{P_NS}}}timing")
        if anchor is None:
            anchor = slide_element.find(f"{{{P_NS}}}extLst")
        if anchor is not None:
            anchor.addprevious(transition)
        else:
            slide_element.append(transition)

    transition.set("advTm", str(delay_ms))
