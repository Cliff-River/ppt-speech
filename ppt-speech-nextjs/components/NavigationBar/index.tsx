"use client";

import {
  Drawer,
  DrawerTrigger,
  DrawerBackdrop,
  DrawerContent,
  DrawerDialog,
  DrawerHeader,
  DrawerHeading,
  DrawerBody,
  DrawerCloseTrigger,
} from "@heroui/react";
import Logo from "./Logo";
import GitHubLink from "./GitHubLink";
import LanguageSelector from "./LanguageSelector";

/**
 * 顶部导航栏组件
 *
 * PressResponder 警告修复要点：
 * 1. Drawer 使用「非受控复合组件」模式：Drawer.Trigger 包裹汉堡按钮作为 Drawer
 *    根组件的直接 pressable child，DrawerBackdrop/DrawerContent 作为同级兄弟，
 *    这样 DialogTriggerPrimitive 内部 PressResponder 能正确找到 pressable child。
 * 2. DrawerDialog 内部必须同时提供 DrawerHeading (slot="title") 和
 *    DrawerCloseTrigger (slot="close")，满足 Dialog 无障碍要求。
 * 3. GitHub 链接不使用 HeroUI Tooltip，改用原生 group-hover 自定义 tooltip。
 *
 * 布局结构：
 * - 左侧：Logo + 应用标题
 * - 右侧：语言选择器 + GitHub链接（桌面端） / 汉堡按钮（移动端）
 */
export default function NavigationBar() {
  return (
    <header>
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
              <LanguageSelector />
              <GitHubLink />
            </div>

            {/*
              移动端：使用 Drawer.Trigger 渲染汉堡按钮
              Drawer.Trigger 本质是 ButtonPrimitive (react-aria Button)，
              自带 usePress 绑定，能正确作为 DrawerRoot 的 pressable child，
              消除 PressResponder 警告。
            */}
            <Drawer>
              <DrawerTrigger
                type="button"
                className="
                  sm:hidden
                  inline-flex items-center justify-center
                  w-10 h-10 rounded-full
                  text-default-600 hover:text-foreground hover:bg-default-100
                  transition-colors duration-200
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2
                  data-slot-override
                "
                aria-label="Open navigation menu"
              >
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
              </DrawerTrigger>

              <DrawerBackdrop>
                <DrawerContent
                  placement="right"
                  className="w-72 max-w-[80vw] mt-16"
                >
                  <DrawerDialog>
                    <DrawerHeader className="flex items-center justify-between px-4 pt-4 pb-2 border-b border-default-200">
                      <DrawerHeading className="text-base font-semibold">
                        Navigation Menu
                      </DrawerHeading>
                      <DrawerCloseTrigger />
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
              </DrawerBackdrop>
            </Drawer>
          </div>
        </div>
      </nav>

      {/* 占位元素 - 防止内容被固定导航栏遮挡 */}
      <div className="h-16" aria-hidden="true" />
    </header>
  );
}
