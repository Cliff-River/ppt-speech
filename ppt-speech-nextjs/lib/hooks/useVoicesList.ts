"use client";

import { useCallback, useMemo, useState } from "react";

import type { Voice, VoiceFilters } from "@/lib/types/voice";
import {
  DEFAULT_VOICE_FILTERS,
  filterVoices,
  getVoiceFilterOptions,
  type VoiceFilterOptions,
} from "@/lib/utils/voiceFilter";

export interface UseVoicesListOptions {
  /** 初始筛选条件（仅在挂载时生效，未提供的字段取默认值） */
  initialFilters?: Partial<VoiceFilters>;
}

export interface UseVoicesListResult {
  /** 应用当前筛选条件后的声音列表 */
  filteredVoices: Voice[];
  /** 当前筛选条件 */
  filters: VoiceFilters;
  /** 从原始声音列表派生的可选筛选项，供 UI 生成下拉选项 */
  availableOptions: VoiceFilterOptions;
  /** 浅合并更新部分筛选条件 */
  setFilters: (patch: Partial<VoiceFilters>) => void;
  /** 重置为初始筛选条件（未指定 initialFilters 时即清空全部条件） */
  resetFilters: () => void;
}

/**
 * 对外部传入的声音列表进行多条件筛选过滤的 Hook。
 *
 * 声音源由调用方通过 `voices` 参数注入（通常来自 useVoiceSource），
 * 本 Hook 只负责筛选状态与派生结果，不发起网络请求。
 *
 * @example
 * ```tsx
 * const { voices } = useVoiceSource();
 * const { filteredVoices, filters, setFilters } = useVoicesList(voices);
 * ```
 */
export const useVoicesList = (
  voices: Voice[],
  options: UseVoicesListOptions = {},
): UseVoicesListResult => {
  const { initialFilters } = options;

  const [filters, setFiltersState] = useState<VoiceFilters>(() => ({
    ...DEFAULT_VOICE_FILTERS,
    ...initialFilters,
  }));

  const setFilters = useCallback((patch: Partial<VoiceFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...patch }));
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState({ ...DEFAULT_VOICE_FILTERS, ...initialFilters });
  }, [initialFilters]);

  const filteredVoices = useMemo(
    () => filterVoices(voices, filters),
    [voices, filters],
  );

  const availableOptions = useMemo(() => getVoiceFilterOptions(voices), [voices]);

  return { filteredVoices, filters, availableOptions, setFilters, resetFilters };
};
