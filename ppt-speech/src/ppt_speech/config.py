"""PPT 配音配置模块（向后兼容重导出）。

本模块从 :mod:`ppt_speech.core.config` 重新导出所有公共符号，
以保持 ``from ppt_speech.config import PTSpeechConfig`` 等既有导入方式可用。
新代码建议直接使用 ``ppt_speech.core.config``。
"""

from ppt_speech.core.config import PptSpeechConfig

__all__ = ["PptSpeechConfig"]