# API 文档

基路径：`/api/v1`。统一错误响应：`{"code": "<错误码>", "detail": "<说明>"}`。

交互式文档：服务启动后访问 `http://<host>:<port>/docs`（Swagger）或 `/redoc`。

## 端点总览

| 方法 | 路径 | 说明 | 成功状态码 |
| --- | --- | --- | --- |
| POST | `/api/v1/tasks` | 上传 pptx 创建处理任务 | 202 |
| GET | `/api/v1/tasks/{task_id}/progress` | SSE 实时进度流 | 200 |
| GET | `/api/v1/tasks/{task_id}` | 查询任务状态 | 200 |
| GET | `/api/v1/tasks/{task_id}/result` | 下载结果 pptx | 200 |
| GET | `/api/v1/tasks` | 列出全部任务 | 200 |
| GET | `/api/v1/health` | 健康检查 | 200 |

---

## POST /api/v1/tasks

上传 pptx 文件并创建后台处理任务。

**请求**：`multipart/form-data`

| 字段 | 类型 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `file` | file | 是 | — | `.pptx` 文件 |
| `voice_name` | string | 否 | `zh-CN-XiaoxiaoNeural` | Edge TTS 语音名称 |
| `speech_rate` | string | 否 | `+0%` | 语速，格式 `[+-]数字%` |
| `auto_advance` | string | 否 | `true` | 是否启用音频后自动翻页（`true`/`false`） |
| `auto_advance_delay` | string | 否 | `2.0` | 自动翻页额外延迟秒数 |

**成功响应** `202`：
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "progress_url": "/api/v1/tasks/550e8400-.../progress",
  "result_url": "/api/v1/tasks/550e8400-.../result"
}
```

**错误**：
| 状态码 | code | 触发条件 |
| --- | --- | --- |
| 400 | `missing_file` | 未上传文件或文件为空 |
| 413 | `too_large` | 超过 `MAX_UPLOAD_MB`（默认 100MB） |
| 422 | `invalid_file_type` | 非 `.pptx` 文件 |
| 422 | `invalid_config` | `voice_name`/`speech_rate`/`auto_advance_delay` 非法 |

---

## GET /api/v1/tasks/{task_id}/progress

SSE 实时进度流。`Content-Type: text/event-stream`。

**事件格式**：`data: <ProgressEvent JSON>\n\n`；心跳：`: keepalive\n\n`（默认 15s）。

```json
{
  "task_id": "550e8400-...",
  "status": "PROCESSING",
  "stage": "SYNTHESIZING",
  "slide_idx": 2,
  "total_slides": 5,
  "percent": 30.0,
  "eta_seconds": 12.5,
  "message": "【第2页】生成语音：...",
  "timestamp": 1785570000.0,
  "error": null,
  "result_ready": false
}
```

客户端应持续读取直到收到 `status` 为 `COMPLETED` 或 `FAILED` 的终态事件后关闭。
任务不存在时，首事件为 `{"status":"FAILED","error":"not found"}` 后流结束。

**ProgressEvent 字段**：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string | 任务 ID |
| `status` | string | `PENDING`/`PROCESSING`/`COMPLETED`/`FAILED` |
| `stage` | string | 处理阶段（见下表） |
| `slide_idx` | int | 当前页码（1-based，非页级为 0） |
| `total_slides` | int | 总页数 |
| `percent` | float | 完成百分比 0.0~100.0 |
| `eta_seconds` | float\|null | 预计剩余秒数（早期为 null） |
| `message` | string | 进度说明 |
| `timestamp` | float | 事件时间戳 |
| `error` | string\|null | 错误信息（FAILED 时） |
| `result_ready` | bool | 结果是否可下载 |

**阶段枚举**：

| stage | 含义 |
| --- | --- |
| `VALIDATING` | 校验配置 |
| `READING_NOTES` | 读取备注 |
| `SYNTHESIZING` | TTS 合成 |
| `EMBEDDING` | 嵌入音频 |
| `SETTING_TRANSITION` | 设置自动翻页 |
| `SAVING` | 保存输出 |
| `COMPLETED` | 处理完成 |
| `FAILED` | 处理失败 |

---

## GET /api/v1/tasks/{task_id}

查询任务状态快照（Redis Hash 内容）。

**成功** `200`：返回任务字段（同 ProgressEvent 的快照，字段为字符串）。
**错误** `404` `not_found`：任务不存在。

---

## GET /api/v1/tasks/{task_id}/result

下载处理结果 pptx。

| 状态码 | code | 说明 |
| --- | --- | --- |
| 200 | — | 返回 pptx 二进制（`application/vnd...presentationml.presentation`） |
| 409 | `not_ready` | 任务未完成（PENDING/PROCESSING） |
| 404 | `failed` | 任务 FAILED（含 `error`） |
| 404 | `not_found` | 任务不存在 |
| 410 | `expired` | 结果文件已过期被清理 |

---

## GET /api/v1/tasks

列出全部任务状态。`200`：`{"tasks": [ <任务快照>, ... ]}`。

---

## GET /api/v1/health

健康检查。

- `200` `{"status":"ok","redis":true,"version":"0.1.0"}`
- `503` `{"status":"degraded","redis":false,"version":"0.1.0"}`
