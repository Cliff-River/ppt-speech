# 客户端使用指南

本项目提供两种客户端使用方式：`client.py` 脚本（命令行联调）与 `test.http`
（REST Client 手动测试）。

## 前置

1. 安装客户端依赖：`uv pip install -e ".[client]"`
2. 启动服务端：`uv run ppt-speech-server`（详见 [部署文档](deployment.md)）

## client.py

`src/client.py`（src 目录下）模拟完整客户端流程：上传 → SSE 实时进度 → 下载结果。

### 命令行参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--server` | `http://127.0.0.1:8000` | 服务端地址 |
| `--input` | （必填） | 输入 pptx 路径 |
| `--voice-name` | `zh-CN-XiaoxiaoNeural` | 语音名称 |
| `--speech-rate` | `+0%` | 语速 |
| `--auto-advance` / `--no-auto-advance` | 启用 | 是否音频后自动翻页 |
| `--auto-advance-delay` | `2.0` | 自动翻页延迟秒数 |
| `--output` | `./output.pptx` | 结果保存路径 |

### 示例

```powershell
uv run python src/client.py `
  --server http://127.0.0.1:8000 `
  --input ./data/input.pptx `
  --voice-name zh-CN-XiaoxiaoNeural `
  --auto-advance `
  --output ./out.pptx
```

### 输出

```
📤 上传文件: ./data/input.pptx
✅ 任务已创建: 550e8400-e29b-41d4-a716-446655440000
📊 实时进度:
[SYNTHESIZING] 第1/5页 10.0% ETA 45.0s — 【第1页】生成语音：...
[EMBEDDING] 第1/5页 15.0% ETA 42.0s — 嵌入音频
...
[COMPLETED] 100% ETA 0.0s — 处理完成
📥 下载结果...
✅ 结果已保存: ./out.pptx
```

退出码：成功 `0`，失败 `1`。

### 工作原理

1. `httpx` POST `/api/v1/tasks`（multipart）→ 获取 `task_id`、`progress_url`、`result_url`。
2. `httpx_sse.EventSource` 异步迭代 `progress_url`，实时打印阶段/百分比/ETA。
3. 收到 `COMPLETED` 后，GET `result_url` 流式写入 `--output`。

## test.http

`test.http`（项目根）供 VS Code REST Client / JetBrains HTTP Client 手动发送请求。

### 使用方法

1. 安装 REST Client 扩展（VS Code）或使用 IntelliJ HTTP Client。
2. 编辑文件顶部的 `@taskId` 变量为实际上传返回的 task_id。
3. 点击每个 `###` 分隔的请求上方的 "Send Request"。

### 覆盖用例

| # | 用例 | 期望 |
| --- | --- | --- |
| 1 | 健康检查 | 200 |
| 2 | 正常上传 | 202 |
| 3 | SSE 进度流 | 200 text/event-stream |
| 4 | 查询状态 | 200 |
| 5 | 列出任务 | 200 |
| 6 | 下载结果 | 200 |
| 7 | 缺文件上传 | 400 |
| 8 | 非法 voice_name | 422 |
| 9 | 非法 speech_rate | 422 |
| 10 | 非法文件类型 | 422 |
| 11 | 不存在任务 | 404 |
| 12 | 结果未就绪 | 409 |

> 注：REST Client 中 SSE（用例 3）为只读流式输出，便于观察事件格式。

## 编程式集成

亦可直接用 HTTP 库集成。关键端点见 [API 文档](api.md)。SSE 消费示例（Python）：

```python
import httpx
from httpx_sse.aio import EventSource

async def watch(server, task_id):
    async with EventSource(f"{server}/api/v1/tasks/{task_id}/progress") as es:
        async for event in es:
            print(event.data)  # ProgressEvent JSON
```
