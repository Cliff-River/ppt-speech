"use client";

import { useLocale } from "next-intl";
import { useRouter, usePathname } from "@/i18n/navigation";
import { Select, ListBox } from "@heroui/react";
import { useTransition, Key } from "react";

/**
 * 语言选择器组件
 * 使用HeroUI Select组件实现语言切换
 * 支持：中文(zh)、英文(en)、法文(fr)、日文(ja)
 *
 * HeroUI v3 Select 说明：
 * - onChange 回调类型为 (value: Key | null) => void
 * - value 类型为 Key (string | number)
 * - 不支持 classNames / size / isLoading 等 v2 属性
 * - 样式通过各子组件 (Trigger / Value / Indicator) 的 className 单独控制
 */
export default function LanguageSelector() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  // 语言选项配置
  const languageOptions = [
    { id: "zh", label: "简体中文", flag: "🇨🇳" },
    { id: "en", label: "English", flag: "🇺🇸" },
    { id: "fr", label: "Français", flag: "🇫🇷" },
    { id: "ja", label: "日本語", flag: "🇯🇵" },
  ];

  // 当前选中的语言选项
  const selectedOption = languageOptions.find((o) => o.id === locale);

  /**
   * 处理语言切换
   * HeroUI v3 onChange 返回 Key | null 类型，需先判空
   */
  const handleLocaleChange = (value: Key | null) => {
    if (!value) return;
    const nextLocale = String(value) as "zh" | "en" | "fr" | "ja";
    if (nextLocale !== locale) {
      startTransition(() => {
        router.replace(pathname, { locale: nextLocale });
      });
    }
  };

  return (
    <Select
      aria-label="Language selection"
      value={locale}
      onChange={handleLocaleChange}
      className="w-auto min-w-35"
    >
      <Select.Trigger
        className={`min-h-9 h-9 px-3 bg-transparent hover:bg-default-100 data-[open=true]:bg-default-100 transition-colors text-sm ${isPending ? "opacity-60 pointer-events-none" : ""}`}
      >
        <Select.Value className="text-sm font-medium">
          {selectedOption ? (
            <span className="flex items-center gap-2">
              <span className="text-base">{selectedOption.flag}</span>
              <span className="hidden sm:inline">{selectedOption.label}</span>
            </span>
          ) : null}
        </Select.Value>
        <Select.Indicator className="text-default-500" />
      </Select.Trigger>
      <Select.Popover className="w-45">
        <ListBox>
          {languageOptions.map((option) => (
            <ListBox.Item
              key={option.id}
              id={option.id}
              textValue={option.label}
              className="px-3 py-2"
            >
              <span className="flex items-center gap-3 w-full">
                <span className="text-lg">{option.flag}</span>
                <span className="text-sm">{option.label}</span>
              </span>
              <ListBox.ItemIndicator />
            </ListBox.Item>
          ))}
        </ListBox>
      </Select.Popover>
    </Select>
  );
}
