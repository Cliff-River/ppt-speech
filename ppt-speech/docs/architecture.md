# 架构文档

## 概述

ppt-speech 在原有命令行/库的基础上扩展为**客户端-服务端架构**：客户端通过
HTTP 上传 `.pptx` 文件，服务端在后台运行「备注提取 → TTS 合成 → 音频嵌入 →
自动翻页 → 保存」流程，并经 **Server-Sent Events (SSE)** 实时回传处理进度
（阶段、完成百分比、预计剩余时间）。处理完成后，客户端下载带配音的结果文件。

**Redis** 作为任务/进度状态存储与 pub/sub 事件广播通道，使 SSE 支持客户端
断线重连与多订阅者。Redis **不缓存** TTS 音频字节或最终 pptx 文件。

## 子包架构

项目代码按职责划分为四个主要子包：

### core 子包 — 业务逻辑与公共功能

`ppt_speech.core` 包含程序的核心处理逻辑，不依赖 server 和 cli 子包。

| 模块 | 职责 |
| --- | --- |
| `core/__init__.py` | 重导出所有公共接口，作为核心 API 入口 |
| `core/config.py` | `PTSpeechConfig` 数据类，处理配置与校验 |
| `core/notes_reader.py` | 从幻灯片提取备注文字 |
| `core/tts_client.py` | Edge TTS 客户端：合成、语音列表、名称规范化 |
| `core/slide_transition.py` | 设置幻灯片自动翻页时序（修改 OOXML advTm） |
| `core/pipeline.py` | 顶层编排：`speak_ppt_notes` / `process_slides`，支持 `on_progress` 回调 |
| `core/audio/` | 音频处理子包 |
| `core/audio/duration.py` | 读取音频时长（基于 tinytag，支持 MP3/WAV 等） |
| `core/audio/embedder.py` | 将 MP3 嵌入幻灯片并配置自动播放 |

### cli 子包 — 命令行界面

`ppt_speech.cli` 提供命令行入口，依赖 core 子包，不依赖 server 子包。

| 模块 | 职责 |
| --- | --- |
| `cli/__init__.py` | 暴露 `main()` 入口 |
| `cli/__main__.py` | 支持 `python -m ppt_speech.cli` 运行 |
| `cli/main.py` | CLI 参数解析（argparse）与入口实现 |
| `cli/voices.py` | 刷新可用语音列表到 `voices.json` |

### server 子包 — 后端服务

`ppt_speech.server` 提供基于 FastAPI 的 HTTP 服务，依赖 core 子包。

| 模块 | 职责 |
| --- | --- |
| `server/app.py` | FastAPI 路由定义 + lifespan 管理 |
| `server/config.py` | `ServerConfig`（从环境变量读取） |
| `server/tasks.py` | `TaskManager`：任务生命周期 + 后台 worker |
| `server/progress.py` | `ProgressReporter` 回调实现 + 事件 schema |
| `server/sse.py` | `event_stream` SSE 生成器 |
| `server/redis_client.py` | `redis.asyncio` 单例 + 键命名 + ping |
| `server/cleanup.py` | 磁盘清理协程 |

### 兼容层（Shell Modules）

根目录下保留了旧模块路径作为兼容层（re-export shell），确保现有导入路径（如 `from ppt_speech.config import PTSpeechConfig`）仍然有效：

- `ppt_speech/config.py` → 重导出 `ppt_speech.core.config`
- `ppt_speech/notes_reader.py` → 重导出 `ppt_speech.core.notes_reader`
- `ppt_speech/tts_client.py` → 重导出 `ppt_speech.core.tts_client`
- `ppt_speech/slide_transition.py` → 重导出 `ppt_speech.core.slide_transition`
- `ppt_speech/pipeline.py` → 重导出 `ppt_speech.core.pipeline`
- `ppt_speech/audio/` → 重导出 `ppt_speech.core.audio`

## 组件分层

```
┌──────────────┐   HTTP/SSE    ┌──────────────────────────────────────┐
│  client.py   │ ────────────▶ │         FastAPI 服务端                │
│ (httpx+sse)  │ ◀──────────── │  server/app.py  路由 + lifespan       │
└──────────────┘   结果下载    │   ├─ server/tasks.py    TaskManager   │
                              │   ├─ server/progress.py ProgressReporter│
                              │   ├─ server/sse.py      event_stream   │
                              │   └─ server/redis_client.py           │
                              └───────────┬──────────────┬─────────────┘
                                          │              │
                          on_progress 回调 │              │ HSET/PUBLISH
                                          ▼              ▼
                              ┌─────────────────┐  ┌──────────────────┐
                              │ core/pipeline   │  │   Redis          │
                              │ process_slides  │  │ task:{id} Hash   │
                              │ (零服务端依赖)   │  │ events:{id} pub  │
                              └─────────────────┘  └──────────────────┘
                                       ▲
                                       │ 共用
                              ┌────────┴────────┐
                              │ cli/main.py      │
                              │ (命令行入口)     │
                              └─────────────────┘
```

## 模块依赖关系

```
cli ──▶ core ◀── server
         ▲
         │ （兼容层重导出）
ppt_speech 根包
```

**依赖规则：**
1. `core` 子包**不依赖** `server` 和 `cli` 子包
2. `server` 和 `cli` 子包可依赖 `core` 子包提供的公共功能
3. 根包的兼容层（shell modules）仅做重导出，不包含业务逻辑
4. 避免循环依赖：`core` → 第三方库（edge-tts, python-pptx, tinytag），`server` → `core` + FastAPI + Redis

## 核心设计原则

### 1. 核心库零服务端依赖
`core/pipeline.py`、`core/config.py`、`core/tts_client.py`、`core/audio/`、`core/notes_reader.py`、
`core/slide_transition.py` **不引入** fastapi/redis 等依赖。进度
通过回调注入（`on_progress: Callable[[dict], None]`）上报，CLI 与服务端共用
同一套编排逻辑：
- **CLI**：`on_progress=None` → 走原 `print` 输出（行为与历史版本逐字一致）。
- **服务端**：`on_progress=ProgressReporter(...)` → 写 Redis Hash + 发 pub/sub。

### 2. 后台任务 + task_id 解耦
上传立即返回 `task_id`（202），处理在独立 asyncio 任务中运行。进度、状态、
结果均按 `task_id` 查询，支持并发任务与 SSE 断线重连。

### 3. Redis 作为状态存储而非文件缓存
按用户决策，Redis 只存任务/进度状态（status/stage/当前页/总页/percent/ETA/
message/error），不缓存 TTS 音频与最终 pptx。大文件存于磁盘
（`work_dir/{task_id}/`），由清理协程按 TTL 过期删除。

## 数据流

1. **上传**：`POST /api/v1/tasks`（multipart）→ 落盘 `work_dir/{task_id}/input.pptx`
   → 校验配置 → 写 Redis `task:{id}` (PENDING) + `tasks:index` → 启动 worker → 返回 202。
2. **处理**：worker 置 PROCESSING → `Presentation(input)` →
   `process_slides(prs, config, on_progress=reporter)`。reporter 每个阶段
   `HSET` 快照 + `PUBLISH` 事件。
3. **进度推送**：`GET /api/v1/tasks/{id}/progress` (SSE) → `HGETALL` 续看首事件
   → 订阅 `events:{id}` 转发 → 终态结束。
4. **完成**：worker 置 COMPLETED（result_ready=true）+ 设 TTL + 删 input。
5. **下载**：`GET /api/v1/tasks/{id}/result` → `FileResponse(output.pptx)`。

## 进度阶段与百分比

阶段序列：`VALIDATING → READING_NOTES → SYNTHESIZING → EMBEDDING →
SETTING_TRANSITION → SAVING → COMPLETED`（异常 → `FAILED`）。

页内权重（每页合计 1.0）：READING_NOTES=0、SYNTHESIZING=0.5、EMBEDDING=0.75、
SETTING_TRANSITION=0.9。`percent = ((idx-1)+weight)/total*100`。
ETA = `elapsed*(100-percent)/percent`（percent≤5 时返回 null 降噪）。

## 并发模型

- 每任务独立 asyncio task + 独立 `work_dir/{task_id}/` 子目录，互不冲突。
- `ProgressReporter.__call__` 为同步回调（匹配 pipeline 同步调用点），内部用
  `asyncio.ensure_future` 调度异步 Redis 写入，不阻塞 pipeline。
- worker 与 reporter 共享同一事件循环。

## 错误处理

- Redis 启动不可达 → fail-fast 拒绝启动（lifespan `ping` 失败）。
- 处理异常 → worker 捕获，置 FAILED + 记录 traceback + 发终态事件 + 删 input。
- SSE 客户端断开 → `try/finally` 退订关 pubsub；worker 继续，可重连续看。
- 任务不存在/过期 → 统一 404（`/progress` 发一条 FAILED 后关闭）。

详见 [API 文档](api.md)、[部署文档](deployment.md)、[缓存策略](caching-strategy.md)。