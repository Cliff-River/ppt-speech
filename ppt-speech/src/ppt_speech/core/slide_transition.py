"""幻灯片自动切换（翻页）控制模块。

通过修改幻灯片底层 OOXML 的 ``<p:transition>`` 元素，设置 ``advTm``
（自动前进时间，毫秒）属性，实现幻灯片在指定时间后自动翻页。

这是 PowerPoint 原生的「切换 → 计时 → 在 X 秒后」机制，
兼容 PowerPoint 2016/2019/365，无需宏或运行时自动化。

.. note::

    按 CT_Slide 的 schema 顺序，``<p:transition>`` 必须位于
    ``<p:cSld>`` / ``<p:clrMapOvr>`` 之后、``<p:timing>`` / ``<p:extLst>``
    之前。本模块在新增元素时严格遵守该顺序，以免 PowerPoint 触发文件修复。

.. note::

    PowerPoint 可能将 ``<p:transition>`` 包裹在 ``<mc:AlternateContent>``
    中以实现多版本兼容（Choice 给新版 Office，Fallback 给旧版）。
    本模块同时处理**直接子元素**和 **mc 包装内**两种情况，确保不会在
    同一个幻灯片下产生两个 ``<p:transition>`` 而触发文件修复。
"""

from __future__ import annotations

from lxml import etree
from pptx.slide import Slide

from ppt_speech.core.audio import P_NS

# OOXML Markup Compatibility 命名空间 URI
_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def _q(ns: str, tag: str) -> str:
    """返回 Clark 表示法的限定标签名 ``{namespace}tag``。"""
    return f"{{{ns}}}{tag}"


def _find_mc_wrapped_transitions(slide_element) -> list:
    """查找幻灯片中被 ``<mc:AlternateContent>`` 包装的所有 ``<p:transition>``。

    在 mc:AlternateContent 内，transition 出现在 mc:Choice 和 mc:Fallback
    子元素中（通常各有一个），本函数将它们全部返回。

    Args:
        slide_element: 幻灯片的 lxml 根元素（``slide._element``）。

    Returns:
        所有被 mc:AlternateContent 包裹的 ``<p:transition>`` 元素列表。
        若无则返回空列表。
    """
    mc_tag = _q(_MC_NS, "AlternateContent")
    p_trans_tag = _q(P_NS, "transition")

    return [
        transition
        for child in slide_element
        if child.tag == mc_tag
        for transition in child.iter(p_trans_tag)
    ]


def _find_direct_transition(slide_element):
    """查找作为幻灯片直接子元素的 ``<p:transition>``。

    Args:
        slide_element: 幻灯片的 lxml 根元素（``slide._element``）。

    Returns:
        ``<p:transition>`` 元素，若无则返回 None。
    """
    return slide_element.find(_q(P_NS, "transition"))


def _remove_empty_direct_transition(slide_element) -> None:
    """清理残留的直接子元素 ``<p:transition>``（本工具先前错误创建的）。

    当原始 PPT 已用 ``<mc:AlternateContent>`` 包装 transition 时，
    本工具旧版本会额外创建一个直接子元素 transition，导致同一幻灯片
    下出现两个 transition 而触发 PowerPoint 文件修复。本函数在发现
    mc 包装的 transition 存在时，负责移除这个多余的直接子元素。
    """
    direct = _find_direct_transition(slide_element)
    if direct is not None:
        slide_element.remove(direct)


def set_advance_after_time(slide: Slide, delay_seconds: float) -> None:
    """设置幻灯片在指定秒数后自动翻页。

    在 ``<p:transition>`` 元素上写入 ``advTm``（毫秒）。若幻灯片已有
    切换设置（含切换效果），仅更新 ``advTm``，保留原有效果；否则按
    schema 顺序新建 ``<p:transition>`` 元素。

    同时处理 ``<mc:AlternateContent>`` 包装的 transition（更新 Choice
    和 Fallback 两个版本的 advTm），并在此情况下清理直接子元素的残留
    transition，避免产生重复元素。

    Args:
        slide: 目标幻灯片对象。
        delay_seconds: 自动翻页延迟时间（秒）。允许为 0，但不能为负数。

    Raises:
        ValueError: 当 ``delay_seconds`` 为负数时。
    """
    if delay_seconds < 0:
        raise ValueError(f"自动翻页延迟时间不能为负数: {delay_seconds}")

    delay_ms = round(delay_seconds * 1000)
    _set_adv_tm(slide._element, delay_ms)


def clear_advance_after_time(slide: Slide) -> bool:
    """清除幻灯片的自动翻页时间（``advTm``）。

    用于重复配音时移除旧的翻页定时：仅删除 ``advTm`` 属性，若
    ``<p:transition>`` 因此成为无任何属性与子元素的空元素（即当初仅为
    ``advTm`` 而创建），则把整个切换元素一并移除，恢复未设置前的状态；
    若切换元素带有切换效果等其它配置，则保留元素与效果。

    同时处理 ``<mc:AlternateContent>`` 包装的 transition。

    Args:
        slide: 目标幻灯片对象。

    Returns:
        是否发生了实际清除（False 表示原本就没有 ``advTm``）。
    """
    return _clear_adv_tm(slide._element)


def _set_adv_tm(slide_element, delay_ms: int) -> None:
    """在幻灯片根元素上设置/更新 ``advTm`` 属性（毫秒）。

    处理策略：

    1. 若存在 ``<mc:AlternateContent>`` 包装的 transition，更新其中所有
       transition（mc:Choice 和 mc:Fallback）的 advTm，并清理可能存在
       的直接子元素残留 transition。
    2. 否则，若存在直接子元素 transition，更新它的 advTm。
    3. 两者都不存在时，按 schema 顺序新建 ``<p:transition>`` 元素。

    Args:
        slide_element: 幻灯片的 lxml 根元素（``slide._element``）。
        delay_ms: 自动前进时间（毫秒）。
    """
    mc_transitions = _find_mc_wrapped_transitions(slide_element)

    if mc_transitions:
        # 有 mc:AlternateContent 包装的 transition：更新里面所有版本，
        # 并清理可能存在的直接子元素残留（本工具旧版本创建的）。
        for t in mc_transitions:
            t.set("advTm", str(delay_ms))
        _remove_empty_direct_transition(slide_element)
        return

    # 没有 mc 包装：处理直接子元素（可能已存在或需新建）
    transition = _find_direct_transition(slide_element)

    if transition is None:
        transition = etree.Element(_q(P_NS, "transition"))
        # 按 CT_Slide schema 顺序插入：位于 p:timing / p:extLst 之前。
        anchor = slide_element.find(_q(P_NS, "timing"))
        if anchor is None:
            anchor = slide_element.find(_q(P_NS, "extLst"))
        if anchor is not None:
            anchor.addprevious(transition)
        else:
            slide_element.append(transition)

    transition.set("advTm", str(delay_ms))


def _clear_adv_tm(slide_element) -> bool:
    """从幻灯片根元素上移除 ``advTm`` 属性。

    同时处理 ``<mc:AlternateContent>`` 包装的 transition（清除 Choice
    和 Fallback 两个版本中的 advTm）以及直接子元素 transition。

    Args:
        slide_element: 幻灯片的 lxml 根元素（``slide._element``）。

    Returns:
        True 表示原存在 ``advTm`` 并已移除；False 表示无需处理。
    """
    changed = False

    # 1. 处理 mc:AlternateContent 包装内的所有 transition
    mc_transitions = _find_mc_wrapped_transitions(slide_element)
    for t in mc_transitions:
        if t.get("advTm") is not None:
            del t.attrib["advTm"]
            changed = True

    # 2. 处理直接子元素 transition
    transition = _find_direct_transition(slide_element)
    if transition is not None:
        if transition.get("advTm") is not None:
            del transition.attrib["advTm"]
            changed = True

        # 仅承载 advTm 的空 <p:transition>：整体移除
        if not transition.attrib and len(transition) == 0:
            slide_element.remove(transition)
            changed = True

    return changed
