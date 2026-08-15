"""支持 ``python -m ppt_speech`` 直接运行完整配音流程。

等价于控制台脚本 ``ppt-speech``（见 ``pyproject.toml`` 与
:func:`ppt_speech.main`）：以 :class:`~ppt_speech.core.config.PTSpeechConfig`
默认配置调用 :func:`~ppt_speech.core.pipeline.speak_ppt_notes`。
"""

from ppt_speech.cli import main

if __name__ == "__main__":
    main()