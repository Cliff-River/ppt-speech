"""支持 ``python -m ppt_speech.server`` 启动 HTTP 服务。

等价于控制台脚本 ``ppt-speech-server``（见 ``pyproject.toml`` 与
:func:`ppt_speech.server.main`）。
"""

from ppt_speech.server import main

if __name__ == "__main__":
    main()
