---
alwaysApply: false
description: 
---
# 项目结构（ppt-speech）

本文件描述仓库的目录结构、各目录职责与放置约束，用于指导新增/修改文件时的归类。团队规范与流程规则见 `docs/development-rules.md`。

## 顶层目录

```
ppt-speech/
├── src/                    # Python 包源码（可复用核心库 + 可选服务端）
│   ├── client.py           # 示例客户端脚本（依赖 [client] extra）
│   └── ppt_speech/         # Python 包（core/server/cli 子包）
├── tests/                  # unittest 测试
├── docs/                   # 架构/API/部署/测试等文档
├── data/                   # 本地输入/输出示例（已 gitignore，不提交）
├── test.http               # REST Client 手工测试用例
├── voices.json             # Edge TTS 语音列表缓存（可再生成）
├── pyproject.toml          # 依赖与脚本入口（uv/PEP621）
├── uv.lock                 # 依赖锁文件（uv 维护）
└── .python-version         # Python 版本固定
```

## 测试与文档

- `tests/`
  - 单元/集成测试，文件命名 `test_*.py`，以 `unittest` 为主。
- `docs/`
  - 面向使用者/贡献者的设计与操作文档（架构、API、部署、测试、缓存与客户端用法）。

## 资源与生成物

- `data/`：仅用于本地调试输入/输出样例，不纳入版本控制。
- `voices.json`：可由工具重新生成（属于缓存/可再生资源），需要时可更新但不作为“唯一数据源”。
