"use client";

import { useState } from "react";
import {
  Drawer,
  DrawerBackdrop,
  DrawerContent,
  DrawerDialog,
  DrawerHeader,
  DrawerBody,
} from "@heroui/react";
import Logo from "./Logo";
import GitHubLink from "./GitHubLink";
import LanguageSelector from "./LanguageSelector";

/**
 * 顶部导航栏组件
 *
 * 功能特性：
 * - 语义化HTML结构，使用<nav>标签
 * - 响应式布局：桌面端左右分布，移动端使用抽屉菜单
 * - 固定在顶部，支持页面滚动时保持可见
 * - 平滑过渡动画与悬停效果
 *
 * HeroUI v3 Drawer 复合组件结构：
 * - Drawer (Root): 状态容器，仅支持 isOpen/onOpenChange/state
 * - Drawer.Backdrop: 遮罩层
 * - Drawer.Content: 内容层 (placement 属性放在这里)
 * - Drawer.Dialog: 对话框容器 (Drag-to-dismiss 区域)
 * - Drawer.Header / Drawer.Body / Drawer.Footer: 内容分区
 *
 * 布局结构：
 * - 左侧：Logo + 应用标题
 * - 右侧：语言选择器 + GitHub链接
 */
export default function NavigationBar() {
  // 移动端抽屉菜单打开状态
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  return (
    <header id="main-navigation">
      {/* 顶部导航栏 - 固定在页面顶部 */}
      <nav
        className="
          fixed top-0 left-0 right-0 z-50
          h-16
          bg-background/80 backdrop-blur-md
          border-b border-default-200/60
          transition-all duration-300 ease-in-out
          supports-backdrop-filter:bg-background/60
        "
        role="navigation"
        aria-label="Main navigation"
      >
        {/* 内容容器 - 水平居中，限制最大宽度 */}
        <div className="h-full mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          {/* 内部布局 - Flex左右排列 */}
          <div className="h-full flex items-center justify-between gap-4">
            {/* 左侧：Logo + 标题 */}
            <div className="flex items-center">
              <Logo />
            </div>

            {/* 右侧：桌面端功能区 */}
            <div className="hidden sm:flex items-center gap-2 sm:gap-3">
              {/* 语言选择器 */}
              <LanguageSelector />

              {/* GitHub链接 */}
              <GitHubLink />
            </div>

            {/* 移动端：汉堡菜单按钮 */}
            <button
              type="button"
              className="
                sm:hidden
                inline-flex items-center justify-center
                w-10 h-10 rounded-full
                text-default-600 hover:text-foreground hover:bg-default-100
                transition-colors duration-200
                focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2
              "
              onClick={() => setIsDrawerOpen(true)}
              aria-label="Open navigation menu"
              aria-expanded={isDrawerOpen}
              aria-controls="mobile-navigation-drawer"
            >
              {/* 汉堡菜单图标 - 三条横线 */}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
                className="w-6 h-6"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
                />
              </svg>
            </button>
          </div>
        </div>
      </nav>

      {/* 移动端抽屉菜单 - HeroUI v3复合结构 */}
      <Drawer isOpen={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
        <DrawerBackdrop />
        <DrawerContent placement="right" className="w-72 max-w-[80vw] mt-16">
          <DrawerDialog>
            <DrawerHeader className="sr-only">
              Navigation Menu
            </DrawerHeader>
            <DrawerBody>
              <div className="flex flex-col gap-1 py-4">
                {/* 移动端语言选择器 */}
                <div className="w-full px-2 py-2">
                  <LanguageSelector />
                </div>

                {/* 分隔线 */}
                <div className="mx-2 my-2 border-t border-default-200" />

                {/* 移动端GitHub链接 */}
                <a
                  href="https://github.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => setIsDrawerOpen(false)}
                  className="
                    flex items-center gap-3 mx-2 px-3 py-2.5 rounded-lg
                    text-default-700 hover:text-foreground hover:bg-default-100
                    transition-colors duration-200
                    text-sm font-medium
                  "
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    className="w-5 h-5"
                    aria-hidden="true"
                  >
                    <path
                      clipRule="evenodd"
                      fillRule="evenodd"
                      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.009-.868-.014-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2Z"
                    />
                  </svg>
                  <span>View on GitHub</span>
                </a>
              </div>
            </DrawerBody>
          </DrawerDialog>
        </DrawerContent>
      </Drawer>

      {/* 占位元素 - 防止内容被固定导航栏遮挡 */}
      <div className="h-16" aria-hidden="true" />
    </header>
  );
}
