/**
 * 声音列表筛选的纯函数逻辑（与 React 无关，可独立测试与复用）。
 *
 * 筛选条件之间为 AND 关系：每次都从传入的原始声音列表出发，
 * 一次性应用全部条件，避免多个条件先后设置时互相覆盖。
 */

import type { Voice, VoiceFilters } from "@/lib/types/voice";

/** 默认筛选条件：不限制任何条件。 */
export const DEFAULT_VOICE_FILTERS: VoiceFilters = {
  keyword: "",
  gender: null,
  language: null,
  locale: null,
  category: null,
  personality: null,
};

/** 筛选项 UI 可选用的取值，全部从声音源数据中派生。 */
export interface VoiceFilterOptions {
  genders: string[];
  languages: string[];
  locales: string[];
  categories: string[];
  personalities: string[];
}

/** 后端数据中个别标签带有多余空白（如 " Novel"），统一去除。 */
const normalizeTag = (tag: string): string => tag.trim();

const toSortedUnique = (values: Iterable<string>): string[] =>
  Array.from(new Set(Array.from(values).filter((value) => value !== ""))).sort((a, b) =>
    a.localeCompare(b),
  );

/**
 * 判断单个声音是否满足关键字：大小写不敏感，匹配
 * ShortName / Name / FriendlyName / Locale 中任意一个字段即可。
 */
function matchesKeyword(voice: Voice, normalizedKeyword: string): boolean {
  return [voice.ShortName, voice.Name, voice.FriendlyName, voice.Locale].some((field) =>
    field.toLocaleLowerCase().includes(normalizedKeyword),
  );
}

/**
 * 根据筛选条件过滤声音列表。
 *
 * 始终从 `voices` 原始列表计算，不修改入参数组。
 */
export function filterVoices(voices: Voice[], filters: VoiceFilters): Voice[] {
  const keyword = filters.keyword.trim().toLocaleLowerCase();
  const gender = filters.gender?.trim() || null;
  const language = filters.language?.trim() || null;
  const locale = filters.locale?.trim() || null;
  // 分类/风格数据本身可能带空白（如 " Novel"），两边都做 trim 后再比较
  const category = filters.category?.trim() || null;
  const personality = filters.personality?.trim() || null;

  return voices.filter((voice) => {
    if (keyword && !matchesKeyword(voice, keyword)) {
      return false;
    }
    if (gender !== null && voice.Gender !== gender) {
      return false;
    }
    if (language !== null && voice.Language !== language) {
      return false;
    }
    if (locale !== null && voice.Locale !== locale) {
      return false;
    }
    if (
      category !== null &&
      !voice.VoiceTag.ContentCategories.map(normalizeTag).includes(category)
    ) {
      return false;
    }
    if (
      personality !== null &&
      !voice.VoiceTag.VoicePersonalities.map(normalizeTag).includes(personality)
    ) {
      return false;
    }
    return true;
  });
}

/**
 * 从声音列表中派生下拉筛选项的全部可选值（去重、排序；标签做 trim）。
 */
export function getVoiceFilterOptions(voices: Voice[]): VoiceFilterOptions {
  const genders = new Set<string>();
  const languages = new Set<string>();
  const locales = new Set<string>();
  const categories = new Set<string>();
  const personalities = new Set<string>();

  for (const voice of voices) {
    genders.add(voice.Gender);
    languages.add(voice.Language);
    locales.add(voice.Locale);
    voice.VoiceTag.ContentCategories.forEach((tag) => {
      categories.add(normalizeTag(tag));
    });
    voice.VoiceTag.VoicePersonalities.forEach((tag) => {
      personalities.add(normalizeTag(tag));
    });
  }

  return {
    genders: toSortedUnique(genders),
    languages: toSortedUnique(languages),
    locales: toSortedUnique(locales),
    categories: toSortedUnique(categories),
    personalities: toSortedUnique(personalities),
  };
}
