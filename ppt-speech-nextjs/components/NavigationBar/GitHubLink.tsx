"use client";

import Image from "next/image";
import { Tooltip } from "@heroui/react";

/**
 * GitHub链接组件
 * 显示GitHub图标并跳转到指定仓库
 * 支持悬停提示和动画效果
 *
 * HeroUI v3 Tooltip 复合组件结构：
 * - Tooltip (Root): 包裹 Trigger + Content，支持 delay/closeDelay
 * - Tooltip.Trigger: 触发元素 (必须是可聚焦元素)
 * - Tooltip.Content: 提示内容 (支持 placement 等属性)
 */
export default function GitHubLink() {
  return (
    <Tooltip delay={150}>
      <Tooltip.Trigger>
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="
            relative w-9 h-9 flex items-center justify-center rounded-full
            text-default-600 hover:text-foreground hover:bg-default-100
            transition-all duration-200 ease-out
            focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2
            active:scale-95
          "
          aria-label="View source code on GitHub"
        >
          <div className="relative w-5 h-5">
            <Image
              src="/icons/github.svg"
              alt="GitHub"
              fill
              className="object-contain"
              sizes="20px"
            />
          </div>
        </a>
      </Tooltip.Trigger>
      <Tooltip.Content placement="bottom">View on GitHub</Tooltip.Content>
    </Tooltip>
  );
}
