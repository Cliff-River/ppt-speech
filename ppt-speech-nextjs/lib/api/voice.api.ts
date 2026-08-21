/**
 * 语音相关 API 调用。
 */

import type { ApiError, ListVoicesResponse, Voice } from "@/lib/types/voice";
import { API_BASE_URL, request } from "./api";

const VOICES_ENDPOINT = "/api/v1/voices";

/**
 * 拉取后端可用语音列表。
 *
 * @see {@link https://developer.mozilla.org/docs/Web/API/fetch fetch}
 */
export async function fetchVoices(
  options?: RequestInit,
): Promise<{ data: Voice[]; ok: true } | { error: ApiError; ok: false }> {
  const url = `${API_BASE_URL}${VOICES_ENDPOINT}`;
  const mergedHeaders: HeadersInit = {
    Accept: "application/json",
    ...(options?.headers as Record<string, string> | undefined),
  };
  const result = await request<ListVoicesResponse>(url, {
    method: "GET",
    ...options,
    headers: mergedHeaders,
  });
  if (!result.ok) return result;
  return { ok: true, data: result.data.voices ?? [] };
}
