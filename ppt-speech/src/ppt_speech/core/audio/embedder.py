"""音频嵌入模块。

负责将 MP3 音频文件嵌入 PowerPoint 幻灯片，并通过修改
底层 XML 配置实现幻灯片进入时音频自动播放。

幂等性保证
==========
对同一份演示文稿重复配音时，:func:`embed_audio_autoplay` 会先调用
:func:`remove_embedded_audio` 清除本工具此前嵌入的旧配音，再嵌入新音频：

1. **形状**：删除旧的媒体形状（``<p:pic>`` 扬声器图标），并删除该形状
   引用的全部关系（``a:videoFile`` / ``p14:media`` / ``a:blip``），
   使旧 MP3 媒体部件在保存时被包图遍历丢弃，文件不会越配音越大。
2. **自动播放时序**：删除 ``<p:timing>`` 下指向被删形状的 ``p:video``
   （或 ``p:audio``）节点；若整个 ``<p:timing>`` 因此恢复为空骨架，
   则整体移除。
3. **识别方式**：新嵌入的形状在 ``cNvPr@descr`` 上携带固定标记
   :data:`_AUDIO_SHAPE_MARKER`；对无标记的历史版本产物，回退按
   ``a:videoFile`` 且对应媒体部件 content-type 为 ``audio/*`` 识别
   （用户自行插入的视频 ``video/*`` 不会被误删）。
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree
from pptx.opc.package import PartFactory
from pptx.parts.media import MediaPart
from pptx.slide import Slide
from pptx.util import Inches

# PowerPoint 主要命名空间 URI
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
# PowerPoint 2010 扩展命名空间 URI（用于媒体元素）
P14_NS = "http://schemas.microsoft.com/office/powerpoint/2010/main"
# DrawingML 命名空间 URI（a:videoFile / a:blip 等）
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
# OPC 关系命名空间 URI（r:link / r:embed）
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# 本工具嵌入的配音形状在 cNvPr@descr 上携带的固定标记，
# 用于在重复配音时精确识别「本工具产生的配音」。
_AUDIO_SHAPE_MARKER = "ppt-speech:dubbing-audio"

# python-pptx 1.0.x 的 PartFactory 仅注册了 video/* 等媒体类型，未注册
# audio/*：重新打开含嵌入 MP3 的演示文稿时，音频部件会被实例化为基类
# Part（没有 sha1 属性），此后 add_movie 内部的媒体去重扫描
# (_MediaParts._find_by_sha1) 会因访问 Part.sha1 抛出
# AttributeError。补注册常见音频类型即可在导入本模块时修复该问题，
# 使「对已配音文件再次配音」成为可能。setdefault 保证未来版本的
# python-pptx 若自行注册不会被覆盖。
_AUDIO_CONTENT_TYPES = (
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4",
    "audio/aac",
    "audio/ogg",
)


def _register_audio_media_part_types() -> None:
    """将常见音频 content-type 补注册到 :class:`PartFactory`。

    使重新加载的音频部件实例化为 :class:`MediaPart`（具备 ``sha1``），
    修复 python-pptx 1.0.x 无法对含音频的演示文稿再次执行 add_movie
    的上游缺陷。
    """
    for content_type in _AUDIO_CONTENT_TYPES:
        PartFactory.part_type_for.setdefault(content_type, MediaPart)


_register_audio_media_part_types()


def _q(ns: str, tag: str) -> str:
    """返回 Clark 表示法的限定标签名 ``{namespace}tag``。"""
    return f"{{{ns}}}{tag}"


def _mark_audio_shape(pic_element) -> None:
    """在媒体形状的 ``cNvPr`` 上写入本工具的固定标记。"""
    cnvpr = pic_element.find(
        f"{_q(P_NS, 'nvPicPr')}/{_q(P_NS, 'cNvPr')}"
    )
    if cnvpr is not None:
        cnvpr.set("descr", _AUDIO_SHAPE_MARKER)


def _rel_targets_audio(slide_part, rId: str) -> bool:
    """判断关系 *rId* 指向的部件是否为音频（content-type 以 ``audio/`` 开头）。

    外部关系、缺失关系或无法解析目标部件时返回 False。
    """
    if not rId or rId not in slide_part.rels:
        return False

    rel = slide_part.rels[rId]
    if getattr(rel, "is_external", False):
        return False

    target_part = getattr(rel, "target_part", None)
    if target_part is None:
        return False
    return str(getattr(target_part, "content_type", "")).startswith("audio/")


def _is_owned_audio_pic(slide_part, pic) -> bool:
    """判断 *pic* 是否为本工具嵌入的配音形状。

    优先依据 cNvPr@descr 上的固定标记精确识别；对历史版本产物（无标记），
    回退要求同时满足：存在 ``a:videoFile`` 且其关系指向音频部件，
    避免误删用户自行插入的视频等媒体。
    """
    cnvpr = pic.find(f"{_q(P_NS, 'nvPicPr')}/{_q(P_NS, 'cNvPr')}")
    if cnvpr is not None and cnvpr.get("descr") == _AUDIO_SHAPE_MARKER:
        return True

    video_file = pic.find(
        f"{_q(P_NS, 'nvPicPr')}/{_q(P_NS, 'nvPr')}/{_q(A_NS, 'videoFile')}"
    )
    if video_file is None:
        return False
    return _rel_targets_audio(slide_part, video_file.get(_q(R_NS, "link")))


def _pic_relationship_ids(pic) -> set[str]:
    """收集媒体形状上媒体/视频/海报帧图片的全部关系 ID。"""
    refs = (
        # a:videoFile r:link —— python-pptx add_movie 生成的视频关系
        (
            f"{_q(P_NS, 'nvPicPr')}/{_q(P_NS, 'nvPr')}/"
            f"{_q(A_NS, 'videoFile')}",
            _q(R_NS, "link"),
        ),
        # p14:media r:embed —— 实际媒体部件
        (
            f"{_q(P_NS, 'nvPicPr')}/{_q(P_NS, 'nvPr')}/"
            f"{_q(P_NS, 'extLst')}/{_q(P_NS, 'ext')}/{_q(P14_NS, 'media')}",
            _q(R_NS, "embed"),
        ),
        # a:blip r:embed —— 扬声器海报帧图片
        (
            f"{_q(P_NS, 'blipFill')}/{_q(A_NS, 'blip')}",
            _q(R_NS, "embed"),
        ),
    )

    rids: set[str] = set()
    for xpath, attr_name in refs:
        element = pic.find(xpath)
        if element is not None:
            value = element.get(attr_name)
            if value:
                rids.add(value)
    return rids


def _remove_media_timing(slide_element, removed_shape_ids: set[str]) -> None:
    """删除指向被删形状的媒体播放时序节点。

    仅处理 ``<p:timing>`` 下的 ``p:video`` / ``p:audio`` 节点（按
    ``p:spTgt@spid`` 与被删形状 ID 匹配）。若删除后整个时序树退化为
    python-pptx 创建的空骨架（仅剩 tmRoot 一个 cTn、无媒体节点、无
    bldLst），则把 ``<p:timing>`` 整体移除；若用户原本有其它动画，
    则保留时序树，只摘除媒体节点。
    """
    if not removed_shape_ids:
        return

    timing = slide_element.find(_q(P_NS, "timing"))
    if timing is None:
        return

    for tag_name in ("video", "audio"):
        for media_node in timing.findall(f".//{_q(P_NS, tag_name)}"):
            spid_el = media_node.find(
                f"./{_q(P_NS, 'cMediaNode')}/"
                f"{_q(P_NS, 'tgtEl')}/{_q(P_NS, 'spTgt')}"
            )
            if (
                spid_el is not None
                and spid_el.get("spid") in removed_shape_ids
            ):
                media_node.getparent().remove(media_node)

    has_media = (
        timing.find(f".//{_q(P_NS, 'video')}") is not None
        or timing.find(f".//{_q(P_NS, 'audio')}") is not None
    )
    root_child_tn_lst = timing.find(
        f"./{_q(P_NS, 'tnLst')}/{_q(P_NS, 'par')}/"
        f"{_q(P_NS, 'cTn')}/{_q(P_NS, 'childTnLst')}"
    )
    is_empty_skeleton = (
        not has_media
        and timing.find(_q(P_NS, "bldLst")) is None
        and len(timing.findall(f".//{_q(P_NS, 'cTn')}")) == 1
        and root_child_tn_lst is not None
        and len(root_child_tn_lst) == 0
    )
    if is_empty_skeleton:
        slide_element.remove(timing)


def remove_embedded_audio(slide: Slide) -> int:
    """清除幻灯片上本工具此前嵌入的全部旧配音。

    删除内容：

    - 带标记（或媒体部件为 ``audio/*`` 的历史版本）媒体形状；
    - 形状引用的媒体/视频/海报帧关系（关系被其它 XML 引用时
      python-pptx 的 ``drop_rel`` 会自行保留）；
    - 对应的自动播放时序节点，以及退化后的空 ``<p:timing>``。

    Args:
        slide: 需要清理的目标幻灯片对象。

    Returns:
        本次清除的旧配音形状数量（0 表示该页没有旧配音）。
    """
    slide_element = slide._element
    slide_part = slide.part

    sp_tree = slide_element.find(
        f"{_q(P_NS, 'cSld')}/{_q(P_NS, 'spTree')}"
    )

    removed_shape_ids: set[str] = set()
    rids_to_drop: set[str] = set()

    if sp_tree is not None:
        for pic in list(sp_tree.iter(_q(P_NS, "pic"))):
            if not _is_owned_audio_pic(slide_part, pic):
                continue

            cnvpr = pic.find(f"{_q(P_NS, 'nvPicPr')}/{_q(P_NS, 'cNvPr')}")
            shape_id = cnvpr.get("id") if cnvpr is not None else None
            if shape_id:
                removed_shape_ids.add(shape_id)

            rids_to_drop.update(_pic_relationship_ids(pic))
            pic.getparent().remove(pic)

    _remove_media_timing(slide_element, removed_shape_ids)

    # 先删 XML 引用再删关系：drop_rel 仅在引用计数为 0/1 时真正移除，
    # 引用仍存在时静默保留，不会破坏部件。
    for rId in rids_to_drop:
        try:
            slide_part.drop_rel(rId)
        except (KeyError, AttributeError):
            pass

    return len(removed_shape_ids)


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
    for media_el in slide_element.iter(_q(P14_NS, "media")):
        media_el.set(_q(P_NS, "playOnEntry"), "1")

    timing = slide_element.find(_q(P_NS, "timing"))
    if timing is None:
        return

    # 2. 调整所有条件：零延迟 + withPrev 并发触发
    for cond in timing.findall(f".//{_q(P_NS, 'cond')}"):
        cond.set("delay", "0")
        if cond.find(_q(P_NS, "withPrev")) is None:
            etree.SubElement(cond, _q(P_NS, "withPrev"))

    # 3. 在媒体节点上再次设置 playOnEntry（兼容不同版本）
    for media_node in timing.findall(f".//{_q(P_NS, 'cMediaNode')}"):
        media_node.set(_q(P_NS, "playOnEntry"), "1")


def embed_audio_autoplay(
    slide: Slide,
    audio_path: Path,
    icon_offset: float = -2.0,
    icon_size: float = 1.0,
) -> int:
    """将音频文件嵌入幻灯片并设置为进入时自动播放。

    嵌入前会先调用 :func:`remove_embedded_audio` 清除该幻灯片上由本工具
    嵌入的旧配音（形状、媒体关系与自动播放时序），因此对同一页重复执行
    不会叠加多个扬声器图标或多段音频，保证重复配音的幂等性。

    首先通过 python-pptx 的 `add_movie` 接口将音频作为媒体资源嵌入，
    在形状上写入本工具标记，之后调用 `_apply_autoplay_timing` 直接修改
    底层 XML 的时序规则，让音频在幻灯片进入时自动触发播放。

    图标默认放置在画布边界外（偏移为负英寸），从而在演示时视觉隐藏。

    Args:
        slide: 需要嵌入音频的目标幻灯片对象。
        audio_path: 本地 MP3 音频文件路径。
        icon_offset: 音频图标左上角偏移（英寸），负值表示在画布外隐藏。
        icon_size: 音频图标尺寸（英寸），必须大于 0。

    Returns:
        嵌入新音频前被清除的旧配音形状数量（0 表示此前没有旧配音）。

    Raises:
        FileNotFoundError: 当 `audio_path` 指向的文件不存在时。
        ValueError: 当 `icon_size` 小于等于 0 时。
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    if icon_size <= 0:
        raise ValueError(f"图标尺寸必须为正数，当前值: {icon_size}")

    removed_count = remove_embedded_audio(slide)

    movie_shape = slide.shapes.add_movie(
        str(audio_path),
        left=Inches(icon_offset),
        top=Inches(icon_offset),
        width=Inches(icon_size),
        height=Inches(icon_size),
        poster_frame_image=None,
        mime_type="audio/mpeg",
    )
    _mark_audio_shape(movie_shape._element)

    _apply_autoplay_timing(slide._element)

    return removed_count
