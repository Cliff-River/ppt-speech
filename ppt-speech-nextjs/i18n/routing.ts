import {defineRouting} from 'next-intl/routing';

export const routing = defineRouting({
  // A list of all locales that are supported
  locales: [ "zh", 'en', "fr", "ja" ],

  // Used when no locale matches
  defaultLocale: "zh",

  // 启用语言检测：会自动按顺序检测 Cookie → Accept-Language Header
  // 默认已为 true，此处显式声明以便理解
  localeDetection: true,

  // 可选：自定义语言 Cookie 配置
  // next-intl 默认会读取名为 "NEXT_LOCALE" 的 Cookie
  // 如果你的 Cookie 名称不同，请在此处修改 name
  // localeCookie: {
  //   name: "NEXT_LOCALE",
  // }
});