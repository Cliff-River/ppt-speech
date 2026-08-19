/**
 * 调用后端语音 API 的工具函数。
 */

import type { ApiError, ListVoicesResponse, Voice } from "@/lib/types/voice";

/**
 * 后端 API 基础路径。
 *
 * 可通过 NEXT_PUBLIC_API_BASE_URL 环境变量覆盖，默认使用相对路径，
 * 依赖 Next.js rewrites / 反向代理将 /api/* 转发到后端服务。
 */
export const API_BASE_URL =
  (typeof process !== "undefined" &&
    (process.env as Record<string, string | undefined>)
      .NEXT_PUBLIC_API_BASE_URL) ||
  "";

const VOICES_ENDPOINT = "/api/v1/voices";

/**
 * 统一的请求封装：处理非 2xx 响应，解析 JSON，并返回结构化错误。
 */
async function request<T>(
  input: string,
  init?: RequestInit,
): Promise<{ data: T; ok: true } | { error: ApiError; ok: false }> {
  try {
    const response = await fetch(input, init);
    const contentType = response.headers.get("content-type") ?? "";
    const isJson = contentType.includes("application/json");

    if (!response.ok) {
      if (isJson) {
        const body = (await response.json()) as Partial<ApiError>;
        return {
          ok: false,
          error: {
            code: body.code ?? `http_${response.status}`,
            detail:
              body.detail ??
              (response.statusText || `HTTP ${response.status}`),
          },
        };
      }
      return {
        ok: false,
        error: {
          code: `http_${response.status}`,
          detail: response.statusText || `HTTP ${response.status}`,
        },
      };
    }

    const data = (isJson ? await response.json() : (await response.text()) as unknown) as T;
    return { ok: true, data };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      ok: false,
      error: {
        code: "network_error",
        detail: message,
      },
    };
  }
}

/**
 * 拉取后端可用语音列表。
 *
 * @see {@link https://developer.mozilla.org/docs/Web/API/fetch fetch}
 */
export async function fetchVoices(
  options?: RequestInit,
): Promise<{ data: Voice[]; ok: true } | { error: ApiError; ok: false }> {
  const url = `${API_BASE_URL}${VOICES_ENDPOINT}`;
  const result = await request<ListVoicesResponse>(url, {
    method: "GET",
    headers: { Accept: "application/json" },
    ...options,
  });
  if (!result.ok) return result;
  return { ok: true, data: result.data.voices ?? [] };
}
