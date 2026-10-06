/**
 * useVoiceSource 集成测试。
 *
 * 与单元测试（lib/hooks/useVoiceSource.test.ts，mock fetchVoices）不同，
 * 本文件不 mock 任何业务模块，Hook -> voice.api -> request -> fetch
 * 全链路真实请求后端服务（uv run ppt-speech-server，默认 http://localhost:8000）。
 *
 * 运行前请确保后端服务已启动；后端地址可通过环境变量覆盖：
 *   NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 pnpm vitest run tests/integration
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Voice } from "@/lib/types/voice";

// API_BASE_URL 在 lib/api/api.ts 模块初始化时读取环境变量并固化，
// 因此必须在动态导入业务模块之前设置好。
const API_ORIGIN =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
process.env.NEXT_PUBLIC_API_BASE_URL = API_ORIGIN;
const VOICES_URL = `${API_ORIGIN}/api/v1/voices`;

// 动态导入确保环境变量先生效
const { useVoiceSource } = await import("@/lib/hooks/useVoiceSource");

/** 直接请求后端，作为契约对照数据 */
async function fetchVoicesDirectly(): Promise<Voice[]> {
  const response = await fetch(VOICES_URL, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`后端不可用: HTTP ${response.status}`);
  }
  const body = (await response.json()) as { voices: Voice[] };
  return body.voices;
}

/** 校验后端返回的单个 Voice 对象符合前端类型契约 */
function expectValidVoice(voice: Voice): void {
  expect(voice).toEqual(
    expect.objectContaining({
      Name: expect.any(String),
      ShortName: expect.any(String),
      Gender: expect.stringMatching(/^(Female|Male)$/),
      Locale: expect.any(String),
      SuggestedCodec: expect.any(String),
      FriendlyName: expect.any(String),
      Status: expect.any(String),
      Language: expect.any(String),
    }),
  );
  expect(Array.isArray(voice.VoiceTag?.ContentCategories)).toBe(true);
  expect(Array.isArray(voice.VoiceTag?.VoicePersonalities)).toBe(true);
}

describe("useVoiceSource 集成测试（真实后端）", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("后端服务可达：GET /api/v1/voices 返回 200 与 voices 数组", async () => {
    const response = await fetch(VOICES_URL, {
      headers: { Accept: "application/json" },
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("application/json");

    const body = (await response.json()) as { voices: unknown[] };
    expect(Array.isArray(body.voices)).toBe(true);
    expect(body.voices.length).toBeGreaterThan(0);
  });

  it("autoFetch（默认）时初始状态为 loading=true、voices 为空", () => {
    const { result } = renderHook(() => useVoiceSource());

    expect(result.current.loading).toBe(true);
    expect(result.current.voices).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it("挂载后自动拉取真实语音列表，数据与后端契约一致", async () => {
    const expectedVoices = await fetchVoicesDirectly();

    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { result } = renderHook(() => useVoiceSource());

    await waitFor(
      () => {
        expect(result.current.loading).toBe(false);
      },
      { timeout: 10_000 },
    );

    // 请求确实以 GET 方式发送到 /api/v1/voices，并携带 Accept: application/json
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [input, init] = fetchSpy.mock.calls[0];
    expect(String(input)).toBe(VOICES_URL);
    expect(init?.method ?? "GET").toBe("GET");
    expect(init?.headers).toMatchObject({ Accept: "application/json" });

    // Hook 数据与直接请求后端的结果完全一致
    expect(result.current.error).toBeNull();
    expect(result.current.voices).toEqual(expectedVoices);

    // 全量校验每个语音对象的结构
    result.current.voices.forEach(expectValidVoice);

    // ShortName 唯一，Gender 仅 Female/Male
    const shortNames = result.current.voices.map((v) => v.ShortName);
    expect(new Set(shortNames).size).toBe(shortNames.length);
    expect(
      result.current.voices.every((v) => v.Gender === "Female" || v.Gender === "Male"),
    ).toBe(true);
  });

  it("返回的列表中包含中文普通话语音 zh-CN-XiaoxiaoNeural", async () => {
    const { result } = renderHook(() => useVoiceSource());

    await waitFor(
      () => {
        expect(result.current.loading).toBe(false);
      },
      { timeout: 10_000 },
    );

    const zhVoice = result.current.voices.find(
      (v) => v.ShortName === "zh-CN-XiaoxiaoNeural",
    );
    expect(zhVoice).toBeDefined();
    expect(zhVoice?.Locale).toBe("zh-CN");
    expectValidVoice(zhVoice as Voice);
  });

  it("autoFetch=false 时挂载不发请求，调用 refresh 后才拉取", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { result } = renderHook(() => useVoiceSource({ autoFetch: false }));

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.loading).toBe(false);
    expect(result.current.voices).toEqual([]);

    await act(async () => {
      await result.current.refresh();
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(String(fetchSpy.mock.calls[0][0])).toBe(VOICES_URL);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.voices.length).toBeGreaterThan(0);
  });

  it("refresh() 可重复拉取，两次结果一致", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { result } = renderHook(() => useVoiceSource({ autoFetch: false }));

    await act(async () => {
      await result.current.refresh();
    });
    const firstVoices = result.current.voices;

    await act(async () => {
      await result.current.refresh();
    });

    expect(fetchSpy).toHaveBeenCalledTimes(2);
    expect(result.current.voices).toEqual(firstVoices);
    expect(result.current.error).toBeNull();
  });

  it("网络异常时错误经 request 全链路透传为 network_error，恢复后 refresh 可重新获取", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementationOnce(() =>
        Promise.reject(new TypeError("Failed to fetch")),
      );

    const { result } = renderHook(() => useVoiceSource({ autoFetch: false }));

    await act(async () => {
      await result.current.refresh();
    });

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(result.current.voices).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toEqual({
      code: "network_error",
      detail: "Failed to fetch",
    });

    // 恢复真实网络后再次 refresh，数据正常返回
    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.error).toBeNull();
    expect(result.current.voices.length).toBeGreaterThan(0);
  });
});
