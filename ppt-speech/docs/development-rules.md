# 项目开发规则（ppt-speech）

本规则用于统一 `ppt-speech` 的目录放置、代码组织、配置与资源管理、协作流程与质量准入标准。所有团队成员必须遵循；如需例外，需在 PR 说明中明确理由与影响范围。

## 1. 目录层级规范

### 1.1 顶层目录职责与放置要求

- `src/`：唯一源码目录。所有可发布/可复用代码必须放在 `src/ppt_speech/` 下。
- `tests/`：唯一测试目录。新增功能必须配套测试，放入 `tests/`，文件名 `test_*.py`。
- `docs/`：唯一文档目录。面向使用者与开发者的说明（API/架构/部署/测试/规范）必须在此维护。
- `data/`：仅本地样例/调试数据（已 `.gitignore`），禁止提交任何真实业务数据或大体积媒体文件。
- 顶层脚本/示例：
  - `client.py`：示例客户端，仅用于演示调用链路；不得在其中堆叠核心逻辑。
  - `test.http`：手工调试用例；只允许存放非敏感的示例请求。
- 构建与依赖：
  - `pyproject.toml`：唯一依赖与脚本入口声明。
  - `uv.lock`：依赖锁文件，必须与 `pyproject.toml` 同步更新。
  - `.python-version`：Python 版本声明，禁止私自降低版本要求。

### 1.2 包内目录职责（src/ppt_speech）

按职责分层，新增文件必须放入最贴近职责的模块中：

- 核心库（无服务端依赖）
  - `config.py`：配置对象与参数校验（不做 I/O，除非校验文件是否存在这类必要检查）。
  - `notes_reader.py`：只负责从 PPT 读取备注文本。
  - `tts_client.py`：只负责 TTS 合成与语音列表处理，不做 PPT 操作。
  - `audio/`：音频相关能力（时长解析、嵌入与自动播放设置）。
  - `slide_transition.py`：只负责翻页/时序写入，不做合成与嵌入。
  - `pipeline.py`：顶层编排与进度回调协议；不得在此新增底层能力实现。
  - `voices.py`：语音列表缓存刷新工具（生成/更新 `voices.json`）。
- 服务端（可选 extra，允许依赖 core）
  - `server/`：FastAPI + Redis + SSE；不得被核心库反向依赖。

### 1.3 命名规范

- Python 文件/目录：`snake_case.py`、`snake_case/`。
- 类名：`PascalCase`；函数与变量：`snake_case`；常量：`UPPER_SNAKE_CASE`。
- 测试文件：`tests/test_<模块或场景>.py`，测试用例方法名清晰表达行为（`test_<行为>_<条件>`）。
- 文档：`docs/<主题>.md`，主题名用短横线 `kebab-case`（与现有 `api.md` 等保持一致）。

## 2. 代码组织标准

### 2.1 分层依赖规则（强制）

依赖方向只允许“上层依赖下层”，禁止反向依赖与环形依赖：

- `ppt_speech.server.*` 可以依赖 `ppt_speech.*`（核心库），但核心库任何模块不得 `import ppt_speech.server.*`。
- `pipeline.py` 可以依赖 `config.py`、`notes_reader.py`、`tts_client.py`、`audio/*`、`slide_transition.py`；反向依赖禁止（底层模块不得依赖 `pipeline.py`）。
- `__init__.py` 仅用于聚合对外公共 API；包内代码不得为了“省路径”而从 `ppt_speech import ...` 回引自身聚合符号，避免产生隐式循环依赖。包内导入优先使用 `from ppt_speech.<module> import ...`。

### 2.2 模块拆分与复用原则

- 单一职责：一个模块只解决一个清晰问题，新增逻辑优先放入最小职责模块而非堆叠到 `pipeline.py`/`server/app.py`。
- 复用优先级：
  - 先复用核心库的函数/类型（`ppt_speech.*`）；
  - 其次在同层新增小模块；
  - 禁止在 `server/` 内复制粘贴核心库逻辑。
- 公共 API 出口：
  - 面向外部调用（CLI/库使用者）的稳定入口必须在 `ppt_speech/__init__.py` 统一导出；
  - 内部模块 API 变更必须同步更新其直接调用方与测试。

### 2.3 I/O 与副作用边界

- 核心库尽量保持“纯逻辑 + 明确 I/O”，避免在低层模块写磁盘/读环境变量。
- 服务端相关的状态存储、任务目录管理、SSE 推送只允许存在于 `ppt_speech/server/`。
- 临时文件必须使用临时目录策略（当前项目已在 `pipeline.py` 实现），禁止在工作区固定生成 `.tmp_*` 目录。

## 3. 配置文件管理

### 3.1 配置分类与位置

- 依赖与构建配置：`pyproject.toml`、`uv.lock`、`.python-version`（顶层）。
- 服务端运行配置：仅通过环境变量注入，并在 `src/ppt_speech/server/config.py` 解析（不得新增“写死在代码里的环境差异”）。
- 本地调试配置：
  - 本项目不提交 `.env`；若需要本地环境变量文件，使用 `.env.local` 并加入 `.gitignore`（新增时必须同步更新 `.gitignore`）。

### 3.2 版本维护规则（强制）

- 修改 `pyproject.toml` 依赖后，必须同步更新 `uv.lock`（用 uv 生成）。
- 不允许直接手工编辑 `uv.lock`。
- 任何会影响 API/行为的配置项变更，必须同步更新对应文档（`README.md` 或 `docs/*`）与测试（如适用）。

### 3.3 环境适配要求

- 生产/测试/本地环境差异必须通过环境变量表达（服务端）或通过显式传参表达（核心库配置对象）。
- 默认值必须“可运行但不危险”：例如工作目录应在系统临时目录，上传大小/TTL 有明确上限，且可被环境变量覆盖。

## 4. 资源文件约束

### 4.1 静态/媒体资源分类

- 可再生缓存：
  - `voices.json`：Edge TTS 语音列表缓存，允许更新；更新需在变更说明中注明生成方式与时间点。
- 本地数据与生成物（禁止提交）：
  - `data/`：输入/输出 PPT；
  - 任何 `.pptx`、音频（`.mp3`/`.wav`）、抓包文件、日志文件、redis dump 等，除非明确标注为“极小、可公开、用于测试”的样例，并经代码审查同意。

### 4.2 引用与路径规范

- 代码中禁止写死绝对路径；必须使用 `pathlib.Path` 并以配置或临时目录传入。
- 服务端生成文件必须落在 `ServerConfig.work_dir` 下，并按 `task_id` 分目录隔离。
- 任何写盘行为必须确保目录存在（`mkdir(parents=True, exist_ok=True)`），并在异常信息中包含可定位的路径信息（但不得包含敏感数据）。

## 5. 协作开发流程

### 5.1 修改范围与“文件所有权”

- `src/ppt_speech/server/`：服务端模块，涉及任务生命周期、Redis 键设计、SSE 协议变更时，必须至少 1 名熟悉服务端的同学审查。
- `src/ppt_speech/`（非 server）：核心库模块，涉及对外 API 或处理链路行为变化时，必须同步更新文档与测试。
- `docs/`：文档变更可独立提交，但若与代码行为相关，必须同 PR 提交。

### 5.2 分支与变更组织

- 分支命名：`feat/<topic>`、`fix/<topic>`、`chore/<topic>`、`docs/<topic>`。
- 提交粒度：
  - 一个提交只解决一个独立问题；
  - 重构与功能变更不得混在同一个提交（除非是必须的机械性修改）。

### 5.3 提交信息规范（强制）

使用 Conventional Commits：

- `feat: ...` 新功能
- `fix: ...` 缺陷修复
- `refactor: ...` 纯重构（不改行为）
- `test: ...` 测试新增/调整
- `docs: ...` 文档变更
- `chore: ...` 工具/依赖/构建调整

提交信息必须包含“影响面”关键词之一：`core` / `server` / `docs` / `tests`（示例：`fix(server): handle redis reconnect`）。

## 6. 质量校验规则

### 6.1 必须通过的检查（准入门槛）

所有合并到主分支的变更必须满足：

- 测试通过：执行（或等价）命令成功
  - `uv run --extra test coverage run -m unittest discover -s tests`
- 不引入循环依赖：满足第 2.1 节依赖规则，核心库不得依赖 `ppt_speech.server`。
- 文档同步：若新增/变更 API、配置项或行为，必须同步更新 `README.md` 或 `docs/*` 中对应章节。

### 6.2 触发条件与自动化建议（可落地）

- 本地提交前（推荐）：
  - 运行单测：`uv run --extra test python -m unittest discover -s tests`
  - 运行覆盖率：`uv run --extra test coverage run -m unittest discover -s tests`
- 合并前（强制）：必须在 PR 描述中贴出测试命令与关键输出（至少包含“OK/FAILED”结果）。
- 后续 CI 建议（如引入 GitHub Actions/其他 CI）：
  - push/PR 自动跑单测与覆盖率；
  - 阻止未通过检查的合并。

### 6.3 代码质量标准（强制）

- 类型与接口：公共函数/方法必须写类型注解；对外结构（如进度事件）必须稳定并有测试覆盖。
- 异常处理：对外暴露的错误信息必须可定位（包含阶段/页码/路径），但不得泄漏敏感信息（如内网密码、Token）。
- 行为兼容：对既有 CLI 行为的改动必须明确（例如是否仍保留原输出、是否改变默认路径），并补测试验证。

