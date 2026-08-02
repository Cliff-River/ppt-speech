
# 项目全局规则

## 项目基础信息

- 项目名称：ppt-speech-nextjs
- 项目描述：PowerPoint 自动配音平台的前端，支持用户上传 ppt 文件，从服务器获取实时进度和下载配音结果。
- 技术栈：Next.js 16 + TypeScript + Tailwind CSS + HeroUI.

## 包管理

- 项目使用 `pnpm` 管理依赖。

## 项目结构

- 使用标准的 Next.js 项目结构。

 ## 开发规范

- 避免单一页面和文件代码过多，通过拆分组件（Component）、模块等方式，将功能点分散到多个文件中，提高代码可维护性。

- 优先使用HeroUI组件库搭建核心界面，样式优先通过Tailwind CSS实现

- 若遇到HeroUI与Tailwind CSS无法实现的 UI 需求，或者其不够美观，可使用原生HTML+CSS补充实现

- 设计页面美观，符合用户习惯。

- 响应式设计，适配不同屏幕尺寸，确保在PC端、移动端等不同环境下都能正常显示与操作。