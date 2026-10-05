"""幻灯片自动切换（翻页）控制模块（向后兼容重导出）。

本模块从 :mod:`ppt_speech.core.slide_transition` 重新导出所有公共符号，
以保持 ``from ppt_speech.slide_transition import ...`` 可用。
"""

from ppt_speech.core.slide_transition import (
    _clear_adv_tm,
    _set_adv_tm,
    clear_advance_after_time,
    set_advance_after_time,
)

__all__ = [
    "set_advance_after_time",
    "clear_advance_after_time",
    "_set_adv_tm",
    "_clear_adv_tm",
]