# 部署文档

## 环境要求

- Python ≥ 3.13
- Redis（默认 `192.168.79.160:6379`，无密码）
- uv 包管理器

## 安装

```powershell
# 克隆后，安装核心库 + 服务端 + 客户端 + 测试依赖
uv pip install -e ".[server,client,test]"
```

可选依赖组（见 `pyproject.toml`）：

| 组 | 包 | 用途 |
| --- | --- | --- |
| `server` | fastapi, uvicorn[standard], redis, python-multipart | 运行 HTTP 服务 |
| `client` | httpx, httpx-sse | 运行 `src/client.py` |
| `test` | coverage, httpx, fakeredis | 运行测试 |

> 核心库（`ppt-speech` CLI）仅需核心依赖，不受 server/client 影响。

## 配置（环境变量）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `REDIS_HOST` | `192.168.79.160` | Redis 地址 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_DB` | `0` | Redis 数据库 |
| `HOST` | `0.0.0.0` | 服务监听地址 |
| `PORT` | `8000` | 服务监听端口 |
| `WORK_DIR` | 系统临时目录下 `ppt_speech_server` | 任务工作目录 |
| `MAX_UPLOAD_MB` | `100` | 上传大小上限（MB） |
| `RESULT_TTL_SECONDS` | `3600` | 终态任务保留时长（秒） |
| `SSE_HEARTBEAT_SECONDS` | `15` | SSE 心跳间隔 |
| `CLEANUP_INTERVAL_SECONDS` | `300` | 磁盘清理扫描间隔 |

## 启动服务

```powershell
# 方式一：控制台脚本
uv run ppt-speech-server

# 方式二：模块入口
uv run python -m ppt_speech.server

# 自定义 Redis 与端口
$env:REDIS_HOST="192.168.79.160"; $env:REDIS_PORT="6379"; $env:PORT="8000"
uv run ppt-speech-server
```

启动时会 `ping` Redis，失败则拒绝启动（fail-fast）。成功后监听 `HOST:PORT`，
交互式文档位于 `/docs`。

## Redis 部署

确保 `192.168.79.160:6379` 可达且无密码（或通过环境变量调整）。连通性验证：

```powershell
Test-NetConnection -ComputerName 192.168.79.160 -Port 6379
```

## 反向代理（Nginx）注意事项

SSE 需要**禁用缓冲**，否则事件会被代理缓存导致延迟/堆积：

```nginx
location /api/v1/tasks/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_buffering off;           # 关键：禁用响应缓冲
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding on;
    proxy_read_timeout 3600s;      # SSE 长连接超时
}
```

服务端已在 SSE 响应头设置 `X-Accel-Buffering: no`，但 Nginx 端仍需
`proxy_buffering off`。

上传大小需与 `MAX_UPLOAD_MB` 一致：

```nginx
client_max_body_size 100m;
```

## 磁盘建议

`WORK_DIR` 存放任务输入/输出 pptx（每个可达数 MB~数十 MB）。建议：
- 单独挂载到容量充足的磁盘。
- 终态任务文件按 `RESULT_TTL_SECONDS`（默认 1 小时）自动清理。
- 高并发场景可适当缩短 `RESULT_TTL_SECONDS` 控制磁盘占用。

## systemd 示例（Linux）

```ini
[Unit]
Description=ppt-speech-server
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/ppt-speech
Environment="REDIS_HOST=192.168.79.160"
Environment="PORT=8000"
ExecStart=/opt/ppt-speech/.venv/bin/ppt-speech-server
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## 健康检查

```powershell
curl http://127.0.0.1:8000/api/v1/health
# {"status":"ok","redis":true,"version":"0.1.0"}
```

Redis 不可达时返回 503，可用于负载均衡健康探针。
