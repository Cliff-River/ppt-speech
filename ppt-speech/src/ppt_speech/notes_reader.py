"""PPT 备注文字读取模块（向后兼容重导出）。

本模块从 :mod:`ppt_speech.core.notes_reader` 重新导出所有公共符号，
以保持 ``from ppt_speech.notes_reader import read_notes_text`` 可用。
"""

from ppt_speech.core.notes_reader import read_notes_text

__all__ = ["read_notes_text"]