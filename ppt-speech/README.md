# ppt-speech

> 一套**以服务端为核心**的 PowerPoint 自动配音平台：在可复用 Python 库与命令行工具之上，主打基于 FastAPI 的 HTTP 服务——上传 `.pptx` 后后台自动将每页备注经 Edge TTS（无需 API Key）合成语音、嵌入幻灯片并按音频时长设置自动翻页，全程经 SSE 实时回传阶段/百分比/ETA 进度，完成后返回带配音的结果文件。底层以 Redis（Hash 快照 + pub/sub 事件）管理任务与进度状态并支持 SSE 断线重连，全部运行参数经环境变量注入、便于容器化部署，对外提供标准 REST + SSE 接口，适用于网课录制、自动讲解、无障碍演示与批量配音等场景的服务端集成。

`ppt-speech` 读取 `.pptx` 文件中每张幻灯片的备注文字，调用 Microsoft Edge 在线文本转语音（TTS）服务生成 MP3 音频，再将音频嵌入对应幻灯片并修改底层 XML 时序，使其在幻灯片进入时自动播放。同时根据每页音频的精确时长，按「音频时长 + n 秒」设置自动切换时间，实现音频播放完成后自动翻页。最终输出一份“自带旁白、自动推进”的演示文稿，适合用于录制网课、自动讲解、无障碍演示等场景。

- 🎙️ 基于 Edge TTS，**无需 API Key**，免费可用
- 📝 以幻灯片“备注”作为旁白文本，无需重复编写讲稿
- ▶️ 翻页即播放，音频图标默认隐藏在画布外
- ⏭️ 音频播放完成后**自动翻页**（音频时长 + 可配置缓冲秒数）
- 🌍 支持多语言/多语音（中文、英文、粤语等数百种 Neural 语音）
- ⚡ 支持语速调节（`+50%` / `-30%` 等）
- 🧩 模块化设计，核心库零外部服务依赖，各子模块可独立导入与测试
- 🖥️ 可选 FastAPI 服务端：文件上传 + SSE 实时进度 + 结果下载（Redis 状态存储）

当前版本：`0.1.0`

---

## 目录

- [核心特性](#核心特性)
- [项目结构](#项目结构)
- [环境要求](#环境要求)
- [安装](#安装)
- [依赖项](#依赖项)
- [使用说明](#使用说明)
- [服务端架构（HTTP + SSE）](#服务端架构http--sse)
- [配置参数](#配置参数)
- [可用语音](#可用语音)
- [开发与测试](#开发与测试)
- [常见问题与已知问题](#常见问题与已知问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [联系方式](#联系方式)

---

## 核心特性

| 特性 | 说明 |
| --- | --- |
| 备注转语音 | 自动提取每张幻灯片的备注文字并合成 MP3 |
| 翻页自动播放 | 通过修改 PPT 底层 XML 时序，实现进入幻灯片即播放 |
| 音频后自动翻页 | 读取每页音频精确时长，按「音频时长 + n 秒」设置自动切换，无需手动点击 |
| 图标隐藏 | 音频图标默认放置在画布边界外（负偏移），演示时不可见 |
| 多语音支持 | 兼容 Edge TTS 全部 Neural 语音（如 `zh-CN-XiaoxiaoNeural`、`en-US-AriaNeural`） |
| 语速调节 | 支持 `[+-]数字%` 格式的语速调整 |
| 配置校验 | 启动前校验语音名称、语速格式及输入文件存在性，快速失败 |
| 临时文件清理 | 处理完成（无论成功与否）后自动清理临时音频目录 |
| 优雅降级 | 某页音频缺失或时长解析失败时仅跳过该页自动翻页，不影响整体流程 |
| 模块化 | 读取、合成、嵌入、编排各层解耦，可单独复用；核心库不依赖 fastapi/redis |
| 客户端-服务端架构 | 基于 FastAPI 的 HTTP 服务，支持文件上传、SSE 实时进度反馈与结果下载 |
| Redis 状态存储 | 任务/进度状态经 Redis Hash + pub/sub 管理，支持 SSE 断线重连 |

## 项目结构

```
ppt-speech/
├── src/
│   └── ppt_speech/
│       ├── __init__.py            # 包入口：包级文档 + 完整公共 API + main()
│       ├── __main__.py            # 支持 python -m ppt_speech 运行完整流程
│       ├── config.py              # PTSpeechConfig 配置类与校验逻辑
│       ├── notes_reader.py        # 从幻灯片提取备注文字
│       ├── tts_client.py          # Edge TTS 客户端（合成、语音列表、名称规范化）
│       ├── audio/                 # 音频处理子包
│       │   ├── __init__.py        # 子包入口：re-export 音频公共接口
│       │   ├── duration.py        # 读取音频时长（基于 tinytag，支持 MP3/WAV 等）
│       │   └── embedder.py        # 将 MP3 嵌入幻灯片并配置自动播放
│       ├── slide_transition.py    # 设置幻灯片自动翻页时序（修改 OOXML advTm）
│       ├── pipeline.py            # 顶层编排：speak_ppt_notes / process_slides（支持 on_progress 回调）
│       ├── voices.py              # 辅助工具：刷新可用语音列表到 voices.json
│       └── server/                # 服务端子包（FastAPI + Redis + SSE，需 [server] extra）
│           ├── __init__.py        # 暴露 main() 控制台入口
│           ├── __main__.py        # 支持 python -m ppt_speech.server
│           ├── config.py          # ServerConfig（env 读取）
│           ├── redis_client.py    # redis.asyncio 单例 + 键命名 + ping
│           ├── progress.py        # ProgressReporter 回调实现 + 事件 schema
│           ├── tasks.py           # TaskManager：任务生命周期 + 后台 worker
│           ├── sse.py             # event_stream SSE 生成器
│           ├── app.py             # FastAPI 路由 + lifespan
│           └── cleanup.py         # 磁盘清理协程
├── tests/                         # 单元/集成测试（unittest）
│   ├── test_notes_tts.py          # 核心库测试
│   ├── test_progress_callback.py  # pipeline 进度回调测试
│   ├── test_redis_client.py       # Redis 客户端 + ProgressReporter 测试
│   ├── test_sse.py                # SSE event_stream 测试
│   ├── test_tasks_lifecycle.py    # TaskManager 生命周期测试
│   └── test_server_app.py         # FastAPI 路由测试
├── docs/                          # 架构/API/部署/缓存/客户端/测试文档
├── data/                          # 输入/输出 PPT 文件目录（已 gitignore）
│   ├── input.pptx
│   └── output.pptx
├── client.py                      # 示例客户端（上传 + SSE + 下载，需 [client] extra）
├── test.http                      # REST Client 测试用例
├── voices.json                    # 可用语音列表缓存（由 python -m ppt_speech.voices 生成）
├── pyproject.toml                 # 项目元数据与依赖声明（含 server/client/test extras）
├── uv.lock                        # uv 锁定的依赖版本
└── .python-version                # Python 版本固定为 3.13
```

## 环境要求

- **Python** ≥ 3.13
- **uv**（推荐的包管理器，用于安装与运行）
- 可访问互联网的 Edge TTS 服务（合成时需要在线）
- **Redis**（仅服务端模式需要，默认 `192.168.79.160:6379`，无鉴权）

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

   `uv sync` 会根据 `uv.lock` 创建虚拟环境并安装核心依赖（`edge-tts`、`python-pptx`、`tinytag`）。
   此外，`pyproject.toml` 中 `[tool.uv] default-groups` 默认启用 `server` 与 `client` 两个依赖组，
   因此 `uv sync` **会一并安装服务端与客户端依赖**（fastapi、uvicorn、redis、httpx 等），
   可直接运行服务端与示例客户端。

3. 按需安装测试依赖：

   ```bash
   # 测试依赖（coverage + httpx + fakeredis）不在默认组内，需单独安装
   uv pip install -e ".[test]"
   # 或临时运行测试时一并拉取（见“开发与测试”一节）：
   # uv run --extra test coverage run -m unittest discover -s tests
   ```

   | 组 | 包 | 用途 | 是否随 `uv sync` 默认安装 |
   | --- | --- | --- | --- |
   | `server` | fastapi, uvicorn[standard], redis, python-multipart | 运行 HTTP 服务 | ✅ 是 |
   | `client` | httpx, httpx-sse | 运行 `client.py` | ✅ 是 |
   | `test` | coverage, httpx, fakeredis | 运行测试 | ❌ 否（需单独安装） |

## 依赖项

### 核心依赖（始终安装）

| 包 | 版本要求 | 用途 |
| --- | --- | --- |
| [`edge-tts`](https://pypi.org/project/edge-tts/) | `>=7.2.8` | 在线 TTS 合成（**无需 API Key**，合成时需联网） |
| [`python-pptx`](https://pypi.org/project/python-pptx/) | `>=1.0.2` | 读写 `.pptx` 与操作幻灯片媒体 |
| [`tinytag`](https://pypi.org/project/tinytag/) | `>=2.3.0` | 纯 Python 读取音频时长（MP3/WAV/M4A/OGG/FLAC），无需 ffmpeg |
| [`lxml`](https://pypi.org/project/lxml/) | （python-pptx 传递依赖，本项目直接使用） | 直接修改底层 OOXML 时序 XML |

### 可选依赖（extras）

| extra | 包 | 用途 |
| --- | --- | --- |
| `[server]` | fastapi, uvicorn[standard], redis, python-multipart | HTTP 服务端 |
| `[client]` | httpx, httpx-sse | 示例客户端脚本 |
| `[test]` | coverage, httpx, fakeredis | 测试套件 |

> 核心库（`pipeline.py` / `config.py` / `tts_client.py` / `audio/` / `notes_reader.py` / `slide_transition.py`）不引入 fastapi/redis 依赖；服务端逻辑隔离在 `ppt_speech/server/` 子包内，作为可选 extra 提供。

## 使用说明

### 快速开始

1. 将待处理的演示文稿放入 `data/` 目录并命名为 `input.pptx`（或在配置中指定其他路径）。
2. 确保每张需要配音的幻灯片已在“备注”区填写讲稿文字。
3. 运行：

   ```bash
   uv run python -m ppt_speech
   ```

   或直接调用控制台入口：

   ```bash
   uv run ppt-speech
   ```

4. 处理完成后，配音后的文件将保存为 `data/output.pptx`，控制台会输出每页的处理进度：

   ```text
   【第1页】生成语音：大家好，今天我们来介绍...
      ⏱️ 第1页自动翻页：音频 12.3s + 缓冲 2.0s = 14.3s
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

## 服务端架构（HTTP + SSE）

除命令行/库外，项目提供基于 FastAPI 的客户端-服务端架构：客户端上传 `.pptx`，
服务端后台处理并经 SSE 实时回传进度（阶段/百分比/ETA），完成后返回带配音的结果。
Redis 作为任务/进度状态存储 + pub/sub 事件通道，支持 SSE 断线重连。

> 详细设计见 [docs/architecture.md](docs/architecture.md)，API 见 [docs/api.md](docs/api.md)，
> 部署见 [docs/deployment.md](docs/deployment.md)，缓存策略见 [docs/caching-strategy.md](docs/caching-strategy.md)。

### 快速开始

```bash
# 1. 安装服务端 + 客户端依赖（uv sync 已默认包含；如未安装可执行）
uv pip install -e ".[server,client]"

# 2. 启动服务（确保 Redis 192.168.79.160:6379 可达）
uv run ppt-speech-server

# 3. 另起终端，运行客户端（实时查看进度 + 下载结果）
uv run python client.py \
  --server http://127.0.0.1:8000 \
  --input ./data/input.pptx \
  --voice-name zh-CN-XiaoxiaoNeural \
  --auto-advance --output ./out.pptx
```

### 主要端点

| 方法 | 路径 | 说明 | 成功状态码 |
| --- | --- | --- | --- |
| POST | `/api/v1/tasks` | 上传 pptx + 配置参数，创建后台任务 | 202 |
| GET | `/api/v1/tasks/{id}/progress` | SSE 实时进度流 | 200 |
| GET | `/api/v1/tasks/{id}` | 查询任务状态 | 200 |
| GET | `/api/v1/tasks/{id}/result` | 下载结果 pptx | 200 |
| GET | `/api/v1/tasks` | 列出全部任务状态 | 200 |
| GET | `/api/v1/health` | 健康检查（含 Redis 连通性） | 200 / 503 |

客户端可传 `voice_name`、`speech_rate`、`auto_advance`、`auto_advance_delay` 参数。
服务启动后访问 `/docs`（Swagger）或 `/redoc` 查看交互式 API 文档。手动测试用例见
[`test.http`](test.http)，客户端使用详见 [docs/client-usage.md](docs/client-usage.md)。

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
| `auto_advance` | `bool` | `True` | 是否启用「音频播放完成后自动翻页」功能；为 `False` 时仅嵌入音频不设置自动切换 |
| `auto_advance_delay` | `float` | `2.0` | 自动翻页缓冲秒数（n），在音频时长基础上额外停留的秒数；启用 `auto_advance` 时不能为负 |

调用 `config.validate()` 会在执行前校验：语音名称格式、语速格式、输入文件是否存在，以及启用自动翻页时 `auto_advance_delay` 不能为负；不合法时分别抛出 `ValueError` / `FileNotFoundError`。

> **语音名称格式**：需匹配 `语言-地区-名称Neural`，例如 `zh-CN-XiaoxiaoNeural`、`en-US-AriaNeural`、`zh-HK-WanLungNeural`。
>
> **语速格式**：需匹配 `[+-]数字%`，例如 `+0%`、`-50%`、`+100%`。

### 自动翻页功能

默认启用（`auto_advance=True`）。开启后，程序会在嵌入音频后读取该页音频的精确时长，并按以下公式设置该幻灯片的自动切换时间：

```
自动停留时间 = 音频时长（秒） + auto_advance_delay（秒，默认 2.0）
```

到达该时间后，PowerPoint 会自动切换至下一页，无需手动点击。

**实现原理**：PowerPoint 原生支持通过幻灯片切换计时（Slide Transition Timing）实现自动翻页，对应 OOXML 中 `<p:transition>` 元素的 `advTm` 属性（单位：毫秒）。但 PowerPoint 原生功能中没有「音频播放结束即翻页」的直接触发器，因此本工具采用「读取音频时长 + 缓冲秒数」的方案，将计算结果写入 `advTm`，从而精确控制每页停留时间。

- **音频时长提取**：使用 [`tinytag`](https://pypi.org/project/tinytag/) 纯 Python 库解析，支持 MP3、WAV、OGG、FLAC 等常见格式，无需安装 ffmpeg 等系统依赖。
- **兼容性**：直接修改 OOXML 时序属性，兼容 PowerPoint 2016 / 2019 / 365 及 WPS 演示。
- **优雅降级**：若某页音频文件缺失或时长解析失败，仅跳过该页的自动翻页设置（打印 `⚠️` 警告），不影响整体配音与保存流程。
- **关闭功能**：将 `auto_advance` 设为 `False` 即可仅嵌入音频而不设置自动切换，保留手动翻页行为。

```python
from pathlib import Path
from ppt_speech import PTSpeechConfig, speak_ppt_notes
import asyncio

config = PTSpeechConfig(
    input_dir=Path("data"),
    output_dir=Path("data"),
    auto_advance=True,          # 启用自动翻页（默认即开启）
    auto_advance_delay=3.0,     # 音频结束后额外停留 3 秒再翻页
)
asyncio.run(speak_ppt_notes(config))
```

## 可用语音

Edge TTS 提供数百种 Neural 语音。运行辅助模块可拉取完整列表并缓存到 `voices.json`：

```bash
uv run python -m ppt_speech.voices
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

测试基于 Python 标准库 `unittest`，覆盖配置校验、语音名称规范化、备注读取、TTS 合成、音频嵌入、音频时长提取、幻灯片自动翻页时序、流程编排、完整流水线（mock），以及服务端的进度回调、Redis 状态存储、SSE 事件流、任务生命周期与 FastAPI 路由：

```bash
# 安装测试依赖（fakeredis 等不在默认组内）
uv pip install -e ".[test]"

# 运行全部测试
uv run coverage run -m unittest discover -s tests -v

# 或一行搞定：临时拉取 test extra 并运行
uv run --extra test coverage run -m unittest discover -s tests -v
```

### 查看覆盖率

```bash
uv run coverage report -m
```

测试不依赖真实网络与真实 Redis（TTS、PPT 保存、Redis 均通过 mock / fakeredis 隔离），
可在离线环境下运行。当前共 98 个测试，整体覆盖率约 95%。测试说明详见
[docs/testing.md](docs/testing.md)。

### 代码风格约定

- 模块顶部使用三引号文档字符串说明职责与编排关系
- 公共函数使用 Google 风格 docstring（含 `Args` / `Returns` / `Raises`）
- 各子模块保持独立、可单独导入与测试，遵循低耦合高内聚
- 类型注解齐全，配合 `from __future__ import annotations`

## 常见问题与已知问题

| 现象 | 原因 | 解决方法 |
| --- | --- | --- |
| 服务启动失败：`无法连接 Redis ... 服务拒绝启动` | `lifespan` 启动时对 Redis `ping` 失败即 fail-fast | 确认 Redis 可达；通过环境变量 `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` 指向正确实例 |
| TTS 合成失败 / `EdgeTTSException` | Edge TTS 需联网；网络中断或服务异常 | 检查网络连通性后重试 |
| 下载结果返回 `409 not_ready` | 任务尚未完成（PENDING/PROCESSING） | 通过 SSE 进度流等待 `status: COMPLETED` 后再请求 `/result` |
| 下载结果返回 `410 expired` | 结果文件超过 `RESULT_TTL_SECONDS`（默认 3600s）被清理协程删除 | 重新提交任务 |
| 某页输出 `⚠️ ... 跳过自动翻页` | 该页音频缺失或时长解析失败（`get_audio_duration` 抛错） | 仅跳过该页自动翻页，不影响整体配音与保存；检查该页音频是否合成成功 |
| 上传返回 `422 invalid_config` | 语音名称或语速格式不合法 | 语音名称需匹配 `语言-地区-名称Neural`，语速需匹配 `[+-]数字%`（见「配置参数」） |
| Windows 重装依赖报 `ppt-speech-server.exe` 被占用 | 服务端进程正在运行，文件被锁定 | 先停止运行中的 `ppt-speech-server` 进程，再重新安装 |
| 幻灯片未生成语音 | 该页备注为空，处理时自动跳过 | 在 PowerPoint「备注」区填写讲稿文字后重新运行 |

> 服务端配置均可通过环境变量覆盖，便于容器化部署，详见 [docs/deployment.md](docs/deployment.md)。

## 贡献指南

欢迎通过 Issue 和 Pull Request 参与贡献！

1. **Fork** 仓库并克隆到本地。
2. 创建特性分支：`git checkout -b feature/your-feature`。
3. 编写代码并补充对应测试，确保现有测试通过：
   ```bash
   uv run --extra test coverage run -m unittest discover -s tests
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
