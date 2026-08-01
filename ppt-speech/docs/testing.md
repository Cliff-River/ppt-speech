# 测试说明

## 测试框架

- 框架：`unittest`（`unittest.IsolatedAsyncioTestCase` 用于异步测试）
- 覆盖率：`coverage`
- Redis 模拟：`fakeredis`（`FakeAsyncRedis` + 共享 `FakeServer` 支持 pub/sub）
- HTTP 测试：FastAPI `TestClient` + `dependency_overrides` 注入伪造依赖

## 测试文件

| 文件 | 覆盖范围 |
| --- | --- |
| `tests/test_notes_tts.py` | 核心库原有测试（配置、TTS、音频、翻页、pipeline） |
| `tests/test_progress_callback.py` | pipeline `on_progress` 回调：事件序列、百分比、print 兼容、2 参调用 |
| `tests/test_redis_client.py` | Redis 键命名、ProgressReporter 写入/广播、set_terminal_state、ping |
| `tests/test_sse.py` | event_stream：不存在/终态/中流转发 |
| `tests/test_tasks_lifecycle.py` | TaskManager：校验失败、成功、异常、列表、结果就绪 |
| `tests/test_server_app.py` | FastAPI 路由：健康、创建（400/413/422/202）、查询、结果（200/409/404/410） |

## 运行测试

```powershell
# 安装测试依赖
uv pip install -e ".[test]"

# 运行全部测试
uv run python -m unittest discover -s tests

# 运行单个测试文件
uv run python -m unittest tests.test_server_app -v
```

## 覆盖率

```powershell
uv run coverage run -m unittest discover -s tests
uv run coverage report -m
```

目标：总覆盖率 ≥ 85%（当前约 94%）。

## 测试要点

### 保持核心库零回归
- `test_notes_tts.py` 中 `speak_ppt_notes` 的精确 2 参调用断言（line 1013）
  由 `pipeline.py` 的分支调用保证：无回调时 `process_slides(prs, config)`，
  有回调时 `process_slides(prs, config, on_progress=...)`。
- `process_slides` 的 `on_progress` 为可选第 3 参，默认 `None`，2 参调用零影响。

### fakeredis pub/sub 时序
fakeredis 异步 pub/sub 投递存在时序，测试中通过轮询 `get_message`（`_await_message`
辅助函数）而非单次读取来可靠获取消息。

### 服务端路由测试
通过 `app.dependency_overrides` 注入伪造的 `TaskManager`、Redis、`ServerConfig`，
并 patch `redis_client.ping` 放行 lifespan 的 fail-fast 校验，避免依赖真实 Redis。

## 本地联调

```powershell
# 1. 起服务（确保 Redis 可达）
$env:REDIS_HOST="192.168.79.160"
uv run ppt-speech-server

# 2. 跑客户端
uv run python client.py --server http://127.0.0.1:8000 `
  --input ./data/input.pptx --output ./out.pptx

# 3. 手动观察 SSE
curl -N http://127.0.0.1:8000/api/v1/tasks/<task_id>/progress

# 4. 用 test.http 验证边界用例
```

成功标准：测试全绿；client 实时滚动进度；`out.pptx` 可下载且含嵌入音频与自动翻页；
Redis 中 `ppt_speech:task:{id}` 终态 COMPLETED。
