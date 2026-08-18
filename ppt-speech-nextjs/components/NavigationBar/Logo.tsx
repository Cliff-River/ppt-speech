"use client";

import Image from "next/image";
import Link from "next/link";
import { useTranslations } from "next-intl";

/**
 * Logo组件 - 显示品牌Logo和应用标题
 * 包含：SVG图标 + 应用名称，支持响应式显示
 */
export default function Logo() {
  const t = useTranslations("app");

  return (
    <Link
      href="/"
      className="flex items-center gap-3 no-underline hover:opacity-90 transition-opacity duration-200"
    >
      {/* Logo图标 */}
      <div className="relative w-10 h-10 shrink-0">
        <Image
          src="/icons/logo.svg"
          alt="Logo"
          fill
          priority
          className="object-contain"
          sizes="40px"
        />
      </div>

      {/* 应用标题 - 移动端隐藏短标题，桌面端显示完整标题 */}
      <span className="hidden sm:block font-bold text-lg text-foreground tracking-tight">
        {t("title")}
      </span>
    </Link>
  );
}
