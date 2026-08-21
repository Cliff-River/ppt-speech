"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchVoices } from "@/lib/api/voice.api";
import type { ApiError, Voice } from "@/lib/types/voice";

export interface UseVoiceSourceOptions {
  /** 组件挂载时是否立即请求，默认 true */
  autoFetch?: boolean;
}

export interface UseVoiceSourceResult {
  voices: Voice[];
  loading: boolean;
  error: ApiError | null;
  /** 重新拉取语音列表 */
  refresh: () => Promise<void>;
}

/**
 * 向后端服务请求可用语音列表的 Hook。
 *
 * @example
 * ```tsx
 * const { voices, loading, error, refresh } = useVoiceSource();
 * ```
 */
export const useVoiceSource = (
  options: UseVoiceSourceOptions = {},
): UseVoiceSourceResult => {
  const { autoFetch = true } = options;

  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState<boolean>(autoFetch);
  const [error, setError] = useState<ApiError | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchVoices();
      if (result.ok) {
        setVoices(result.data);
      } else {
        setError(result.error);
        setVoices([]);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError({ code: "hook_unexpected_error", detail: message });
      setVoices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (autoFetch) {
      queueMicrotask(() => {
        void refresh();
      });
    }
  }, [autoFetch, refresh]);

  return { voices, loading, error, refresh };
};
