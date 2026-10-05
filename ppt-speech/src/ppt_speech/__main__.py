"""支持 ``python -m ppt_speech`` 调用命令行入口。

等价于控制台脚本 ``ppt-speech``（见 ``pyproject.toml`` 与
:func:`ppt_speech.cli.main.main`）：不带任何参数时打印顶层帮助，
传入 ``create`` / ``voice`` 子命令时执行对应流程。
"""

from ppt_speech.cli import main

if __name__ == "__main__":
    main()