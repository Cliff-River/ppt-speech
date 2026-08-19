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
