# 缓存策略文档

## 设计决策

经需求确认，**Redis 仅用于存储任务与进度状态，不缓存 TTS 音频字节或最终 pptx
文件**。本文件阐述该决策的依据与具体策略。

## Redis 中存储的内容

### 1. 任务状态快照（Hash）

- **键**：`ppt_speech:task:{task_id}`
- **类型**：Hash
- **字段**：`task_id`、`status`、`stage`、`slide_idx`、`total_slides`、
  `percent`、`eta_seconds`、`message`、`created_at`、`updated_at`、
  `input_filename`、`error`、`result_ready`
- **TTL**：创建时无 TTL；进入终态（COMPLETED/FAILED）后 `EXPIRE {RESULT_TTL_SECONDS}`
  （默认 3600s），供客户端在下载窗口内查询与下载。

### 2. 实时事件频道（Pub/Sub）

- **频道**：`ppt_speech:events:{task_id}`
- **内容**：进度事件 JSON（`ProgressEvent`）
- **用途**：SSE 订阅者实时接收；支持多订阅者与断线重连。
- **生命周期**：频道无持久化，订阅者断开即消失；最新状态由 Hash 快照兜底。

### 3. 任务索引（Set）

- **键**：`ppt_speech:tasks:index`
- **内容**：全部 `task_id`
- **用途**：`GET /api/v1/tasks` 列表查询。
- **TTL**：无（长期保留）。终态任务的 Hash 过期后，索引中的 task_id 对应
  查询返回空，可在后续优化中清理。

## 不缓存的内容及理由

| 内容 | 存放位置 | 不入 Redis 的理由 |
| --- | --- | --- |
| TTS MP3 音频字节 | 临时目录（处理中，结束清理） | 体积大、生命周期短（仅处理期间需要）、写入 Redis 增加内存压力无收益 |
| 最终 output.pptx | `work_dir/{task_id}/output.pptx` | 体积大（可达数 MB~数十 MB），磁盘更适合；Redis 内存应保留给高频状态查询 |
| 上传 input.pptx | `work_dir/{task_id}/input.pptx` | 处理完成即删除；无需缓存 |

**核心权衡**：Redis 的价值在于低延迟的状态查询与 pub/sub 广播，而非大对象存储。
任务/进度状态是高频读（SSE 重连、状态轮询）、小体积、强时效的数据，最适合 Redis。
大文件交给磁盘 + TTL 清理协程。

## 磁盘清理策略

- 处理完成后**立即删除** `input.pptx`，保留 `output.pptx` 供下载。
- `cleanup.cleanup_loop` 协程每 `CLEANUP_INTERVAL_SECONDS`（默认 300s）扫描
  `work_dir/*`，删除 `mtime` 早于 `RESULT_TTL_SECONDS`（默认 3600s）的子目录。
- 与 Redis Hash TTL 协同：Hash 过期后状态不可查，磁盘文件由协程清理。

## 任务状态机

```
PENDING ──(worker 取出)──▶ PROCESSING ──┬──▶ COMPLETED (result_ready=true)
                                        └──▶ FAILED (error=traceback)
```

终态后均设 TTL，进入下载窗口；窗口过后 Hash 与磁盘文件相继清理。

## 缓存键命名约定

| 用途 | 键 | TTL |
| --- | --- | --- |
| 任务状态 | `ppt_speech:task:{task_id}` | 终态后 3600s |
| 事件频道 | `ppt_speech:events:{task_id}` | 无（pub/sub） |
| 任务索引 | `ppt_speech:tasks:index` | 无 |

## Redis 连接

- 地址：`192.168.79.160:6379`（无密码，可通过 `REDIS_HOST`/`REDIS_PORT`/`REDIS_DB` 覆盖）。
- 客户端：`redis.asyncio.Redis(decode_responses=True)`，模块级单例。
- 启动时 `ping` 校验，失败 fail-fast 拒绝启动。
- 运行中掉线：`ProgressReporter` 写入失败不阻断 pipeline（静默捕获）；`/health` 反映 503。
