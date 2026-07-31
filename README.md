# ppt-speech

> 将 PowerPoint 幻灯片备注自动转换为语音，并嵌入到演示文稿中实现翻页自动播放的命令行工具。

`ppt-speech` 读取 `.pptx` 文件中每张幻灯片的备注文字，调用 Microsoft Edge 在线文本转语音（TTS）服务生成 MP3 音频，再将音频嵌入对应幻灯片并修改底层 XML 时序，使其在幻灯片进入时自动播放。最终输出一份“自带旁白”的演示文稿，适合用于录制网课、自动讲解、无障碍演示等场景。

- 🎙️ 基于 Edge TTS，**无需 API Key**，免费可用
- 📝 以幻灯片“备注”作为旁白文本，无需重复编写讲稿
- ▶️ 翻页即播放，音频图标默认隐藏在画布外
- 🌍 支持多语言/多语音（中文、英文、粤语等数百种 Neural 语音）
- ⚡ 支持语速调节（`+50%` / `-30%` 等）
- 🧩 模块化设计，各子模块可独立导入与测试

---

## 目录

- [核心特性](#核心特性)
- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [安装](#安装)
- [使用说明](#使用说明)
- [配置参数](#配置参数)
- [可用语音](#可用语音)
- [开发与测试](#开发与测试)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [联系方式](#联系方式)

---

## 核心特性

| 特性 | 说明 |
| --- | --- |
| 备注转语音 | 自动提取每张幻灯片的备注文字并合成 MP3 |
| 翻页自动播放 | 通过修改 PPT 底层 XML 时序，实现进入幻灯片即播放 |
| 图标隐藏 | 音频图标默认放置在画布边界外（负偏移），演示时不可见 |
| 多语音支持 | 兼容 Edge TTS 全部 Neural 语音（如 `zh-CN-XiaoxiaoNeural`、`en-US-AriaNeural`） |
| 语速调节 | 支持 `[+-]数字%` 格式的语速调整 |
| 配置校验 | 启动前校验语音名称、语速格式及输入文件存在性，快速失败 |
| 临时文件清理 | 处理完成（无论成功与否）后自动清理临时音频目录 |
| 模块化 | 读取、合成、嵌入、编排各层解耦，可单独复用 |

## 项目结构

```
ppt-speech/
├── src/
│   ├── main.py                    # 辅助脚本：拉取并保存可用语音列表到 voices.json
│   └── ppt_speech/
│       ├── __init__.py            # 包入口，导出公共 API
│       ├── config.py              # PTSpeechConfig 配置类与校验逻辑
│       ├── notes_reader.py        # 从幻灯片提取备注文字
│       ├── tts_client.py          # Edge TTS 客户端（合成、语音列表、名称规范化）
│       ├── audio_embedder.py      # 将 MP3 嵌入幻灯片并配置自动播放
│       └── notes_tts.py           # 顶层编排：speak_ppt_notes / process_slides
├── tests/
│   └── test_notes_tts.py          # 单元测试与集成测试（unittest）
├── data/                          # 输入/输出 PPT 文件目录（已 gitignore）
│   ├── input.pptx
│   └── output.pptx
├── voices.json                    # 可用语音列表缓存（由 src/main.py 生成）
├── pyproject.toml                 # 项目元数据与依赖声明
├── uv.lock                        # uv 锁定的依赖版本
└── .python-version                # Python 版本固定为 3.13
```

## 环境要求

- **Python** ≥ 3.13
- **uv**（推荐的包管理器，用于安装与运行）
- 可访问互联网的 Edge TTS 服务（合成时需要在线）

## 安装

本项目使用 [uv](https://docs.astral.sh/uv/) 管理依赖与虚拟环境。

1. 安装 uv（如尚未安装）：

   ```bash
   # macOS / Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. 克隆仓库并安装依赖：

   ```bash
   git clone <仓库地址>
   cd ppt-speech
   uv sync
   ```

   `uv sync` 会自动根据 `uv.lock` 创建虚拟环境并安装 `edge-tts`、`python-pptx` 等依赖。

## 使用说明

### 快速开始

1. 将待处理的演示文稿放入 `data/` 目录并命名为 `input.pptx`（或在配置中指定其他路径）。
2. 确保每张需要配音的幻灯片已在“备注”区填写讲稿文字。
3. 运行：

   ```bash
   uv run python -m ppt_speech.notes_tts
   ```

   或直接调用包入口：

   ```bash
   uv run ppt-speech
   ```

4. 处理完成后，配音后的文件将保存为 `data/output.pptx`，控制台会输出每页的处理进度：

   ```text
   【第1页】生成语音：大家好，今天我们来介绍...
   【第2页】无备注，跳过配音
   ...
   ✅ 处理完成！输出文件：data/output.pptx
   ```

### 作为库调用

各模块均可独立导入使用。例如自定义配置并执行完整流程：

```python
import asyncio
from pathlib import Path

from ppt_speech import PTSpeechConfig, speak_ppt_notes

config = PTSpeechConfig(
    input_dir=Path("data"),
    output_dir=Path("data"),
    input_filename="input.pptx",
    output_filename="output.pptx",
    voice_name="zh-CN-XiaoxiaoNeural",
    speech_rate="+0%",
)

asyncio.run(speak_ppt_notes(config))
```

单独使用某一子模块（例如仅把文字合成 MP3）：

```python
import asyncio
from pathlib import Path
from ppt_speech.tts_client import text_to_mp3

asyncio.run(text_to_mp3(
    "你好，世界",
    Path("hello.mp3"),
    voice_name="zh-CN-XiaoxiaoNeural",
    speech_rate="-10%",
))
```

## 配置参数

所有参数集中在 [`PTSpeechConfig`](src/ppt_speech/config.py) 数据类中：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `input_dir` | `Path` | `data` | 输入 PPT 所在目录 |
| `output_dir` | `Path` | `data` | 输出 PPT 所在目录 |
| `input_filename` | `str` | `input.pptx` | 输入文件名 |
| `output_filename` | `str` | `output.pptx` | 输出文件名 |
| `voice_name` | `str` | `zh-CN-XiaoxiaoNeural` | Edge TTS 语音名称 |
| `speech_rate` | `str` | `+0%` | 语速，格式为 `[+-]数字%` |
| `temp_audio_dir` | `Path \| None` | `None` | 临时音频目录；为 `None` 时使用系统临时目录（`tempfile`），处理完成后自动清理 |
| `audio_icon_offset` | `float` | `-2.0` | 音频图标偏移（英寸），负值隐藏在画布外 |
| `audio_icon_size` | `float` | `1.0` | 音频图标尺寸（英寸），必须大于 0 |

调用 `config.validate()` 会在执行前校验：语音名称格式、语速格式、输入文件是否存在；不合法时分别抛出 `ValueError` / `FileNotFoundError`。

> **语音名称格式**：需匹配 `语言-地区-名称Neural`，例如 `zh-CN-XiaoxiaoNeural`、`en-US-AriaNeural`、`zh-HK-WanLungNeural`。
>
> **语速格式**：需匹配 `[+-]数字%`，例如 `+0%`、`-50%`、`+100%`。

## 可用语音

Edge TTS 提供数百种 Neural 语音。运行辅助脚本可拉取完整列表并缓存到 `voices.json`：

```bash
uv run python src/main.py
```

`voices.json` 中每项包含 `Name`、`Locale`、`Gender` 等字段，可据此挑选合适的 `voice_name`。常用语音示例：

| 语音名称 | 语言 | 性别 |
| --- | --- | --- |
| `zh-CN-XiaoxiaoNeural` | 普通话（中国大陆） | 女 |
| `zh-CN-YunxiNeural` | 普通话（中国大陆） | 男 |
| `zh-HK-WanLungNeural` | 粤语（中国香港） | 男 |
| `en-US-AriaNeural` | 英语（美国） | 女 |
| `en-US-GuyNeural` | 英语（美国） | 男 |

## 开发与测试

### 运行测试

测试基于 Python 标准库 `unittest`，覆盖配置校验、语音名称规范化、备注读取、TTS 合成、音频嵌入、流程编排及完整流水线（mock）：

```bash
uv run --with coverage --group test coverage run -m unittest discover -s tests -v
```

### 查看覆盖率

```bash
uv run --with coverage --group test coverage report -m
```

测试不依赖真实网络（TTS 与 PPT 保存均通过 mock 隔离），可在离线环境下运行。

### 代码风格约定

- 模块顶部使用三引号文档字符串说明职责与编排关系
- 公共函数使用 Google 风格 docstring（含 `Args` / `Returns` / `Raises`）
- 各子模块保持独立、可单独导入与测试，遵循低耦合高内聚
- 类型注解齐全，配合 `from __future__ import annotations`

## 贡献指南

欢迎通过 Issue 和 Pull Request 参与贡献！

1. **Fork** 仓库并克隆到本地。
2. 创建特性分支：`git checkout -b feature/your-feature`。
3. 编写代码并补充对应测试，确保现有测试通过：
   ```bash
   uv run --with coverage --group test coverage run -m unittest discover -s tests
   ```
4. 保持与现有代码风格一致（docstring、类型注解、模块化）。
5. 提交清晰的 commit message，描述“为什么”而不仅是“做了什么”。
6. 发起 Pull Request，在描述中说明改动目的、影响范围与测试结果。

**提交规范建议：**

- `feat:` 新功能
- `fix:` Bug 修复
- `refactor:` 重构（不改变行为）
- `docs:` 文档更新
- `test:` 测试补充
- `chore:` 构建/工具类杂项

## 许可证

本项目当前未声明开源许可证，版权归作者所有。如需使用、分发或二次开发，请先联系作者确认授权。

## 联系方式

- **作者**：Cliff Huang
- **邮箱**：hzf510920@163.com

如有问题或建议，欢迎通过 Issue 或邮件联系。
