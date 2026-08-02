# ppt-speech

前后端分离的 PowerPoint 自动配音平台：

- 后端 `ppt-speech/`：FastAPI + Redis + SSE，负责将 PPT 备注合成语音、嵌入音频并输出结果文件
- 前端 `ppt-speech-nextjs/`：Next.js + HeroUI + Tailwind，负责语音选择、上传任务、实时进度与下载

## 快速开始（本地联调）

### 1) 启动后端

```bash
cd ppt-speech
uv run python -m ppt_speech.server
```

后端默认提供：

- `GET /api/v1/voices`：语音列表
- `POST /api/v1/tasks`：上传 PPTX 创建任务
- `GET /api/v1/tasks/{id}/progress`：SSE 进度
- `GET /api/v1/tasks/{id}/result`：下载结果

更多接口详见 [api.md](file:///e:/Documents/Projects/ppt-speech/ppt-speech/docs/api.md)。

### 2) 启动前端

```bash
cd ../ppt-speech-nextjs
pnpm install
pnpm dev
```

前端通过 Next.js rewrites 将 `/api/v1/*` 代理到后端，可用环境变量配置后端地址：

```bash
BACKEND_ORIGIN=http://127.0.0.1:8000
```

打开：

- http://localhost:3000/zh
- http://localhost:3000/en
- http://localhost:3000/fr
- http://localhost:3000/ja

## 许可证

本项目采用 MIT License，详见 [LICENSE](file:///e:/Documents/Projects/ppt-speech/LICENSE)。

