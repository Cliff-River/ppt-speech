/**
 * 语音列表相关的类型定义。
 *
 * 结构与后端 voices.json 及 /api/v1/voices 返回值保持一致。
 */

export type VoiceGender = "Female" | "Male";

export interface VoiceTag {
  ContentCategories: string[];
  VoicePersonalities: string[];
}

export interface Voice {
  Name: string;
  ShortName: string;
  Gender: VoiceGender | string;
  Locale: string;
  SuggestedCodec: string;
  FriendlyName: string;
  Status: string;
  VoiceTag: VoiceTag;
  Language: string;
}

export interface ListVoicesResponse {
  voices: Voice[];
}

export interface ApiError {
  code: string;
  detail: string;
}

/**
 * 声音列表筛选条件。
 *
 * 所有条件之间为 AND（同时满足）关系；`null` 或空字符串表示不限制该条件。
 */
export interface VoiceFilters {
  /** 关键字：大小写不敏感地模糊匹配 ShortName / Name / FriendlyName / Locale */
  keyword: string;
  /** 性别；`null` 表示不限 */
  gender: VoiceGender | null;
  /** 语言代码（对应 Voice.Language，如 "zh"、"en"）；`null` 表示不限 */
  language: string | null;
  /** 区域代码（对应 Voice.Locale，如 "zh-CN"、"en-US"）；`null` 表示不限 */
  locale: string | null;
  /** 内容分类（VoiceTag.ContentCategories 中的某一项，如 "News"）；`null` 表示不限 */
  category: string | null;
  /** 语音风格（VoiceTag.VoicePersonalities 中的某一项，如 "Friendly"）；`null` 表示不限 */
  personality: string | null;
}
