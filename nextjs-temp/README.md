# ppt-speech-nextjs

PPT 自动配音平台前端（Next.js App Router）：选择语音 → 上传 `.pptx` 创建任务 → SSE 实时查看进度 → 下载最终“嵌入音频”的结果文件。

## 功能概览

- 语音列表：启动后从后端拉取 voices，并支持搜索/性别/语言-地区联动/Multilingual/风格筛选
- 排序：中文语音优先，其次英文，其余按 Locale 与名称排序
- 任务：上传 `.pptx` 创建任务，自动连接 SSE 推送进度；完成后可一键下载
- 本地持久化：最近 5 个语音、历史任务列表（含断线重连）
- 国际化：`/zh`、`/en`、`/fr`、`/ja` 四语言路由
- UI：优先使用 HeroUI + Tailwind CSS

## 环境要求

- Node.js 20+
- pnpm 11+

## 配置

本项目前端默认把 `/api/v1/*` 反向代理到后端服务（Next.js rewrites）。

通过环境变量配置后端地址：

- `BACKEND_ORIGIN`：后端服务地址（默认 `http://127.0.0.1:8000`）

建议在本目录创建 `.env.local`：

```bash
BACKEND_ORIGIN=http://127.0.0.1:8000
```

## 本地开发

1. 启动后端（另开终端）：

   ```bash
   cd ../ppt-speech
   uv run python -m ppt_speech.server
   ```

2. 启动前端：

   ```bash
   pnpm install
   pnpm dev
   ```

3. 打开：

- http://localhost:3000/zh
- http://localhost:3000/en
- http://localhost:3000/fr
- http://localhost:3000/ja

## 测试与质量

```bash
pnpm lint
pnpm test
pnpm build
```
