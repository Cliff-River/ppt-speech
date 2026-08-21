import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useVoiceSource } from "./useVoiceSource";
import type { Voice, ApiError } from "@/lib/types/voice";

// 模拟 fetchVoices API 函数
vi.mock("@/lib/api/voice.api", () => ({
  fetchVoices: vi.fn(),
}));

import { fetchVoices } from "@/lib/api/voice.api";

const mockVoices: Voice[] = [
  {
    Name: "Voice 1",
    ShortName: "zh-CN-Test1",
    Gender: "Female",
    Locale: "zh-CN",
    SuggestedCodec: "mp3",
    FriendlyName: "Test Voice 1",
    Status: "GA",
    VoiceTag: {
      ContentCategories: ["News"],
      VoicePersonalities: ["Friendly"],
    },
    Language: "Chinese",
  },
  {
    Name: "Voice 2",
    ShortName: "en-US-Test2",
    Gender: "Male",
    Locale: "en-US",
    SuggestedCodec: "mp3",
    FriendlyName: "Test Voice 2",
    Status: "GA",
    VoiceTag: {
      ContentCategories: ["Conversation"],
      VoicePersonalities: ["Professional"],
    },
    Language: "English",
  },
];

describe("useVoiceSource", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("initial state with autoFetch=true (default)", () => {
    it("should return correct initial state before fetch completes", () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);
      // 使用 pending promise，让 fetch 不立即 resolve
      type FetchVoicesResult = Awaited<ReturnType<typeof fetchVoices>>;
      let resolveFetch: (value: FetchVoicesResult | PromiseLike<FetchVoicesResult>) => void;
      fetchVoicesMock.mockImplementation(
        () =>
          new Promise<FetchVoicesResult>((resolve) => {
            resolveFetch = resolve;
          }),
      );

      const { result } = renderHook(() => useVoiceSource());

      // autoFetch 默认 true，所以 loading 初始为 true
      expect(result.current.loading).toBe(true);
      expect(result.current.voices).toEqual([]);
      expect(result.current.error).toBeNull();
      expect(typeof result.current.refresh).toBe("function");
    });

    it("should fetch voices on mount and update state on success", async () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);
      fetchVoicesMock.mockResolvedValue({
        ok: true,
        data: mockVoices,
      });

      const { result } = renderHook(() => useVoiceSource());

      // 等待刷新完成
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(fetchVoicesMock).toHaveBeenCalledTimes(1);
      expect(result.current.voices).toEqual(mockVoices);
      expect(result.current.error).toBeNull();
    });

    it("should set error and empty voices on API error response", async () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);
      const mockError: ApiError = {
        code: "http_500",
        detail: "Server error",
      };
      fetchVoicesMock.mockResolvedValue({
        ok: false,
        error: mockError,
      });

      const { result } = renderHook(() => useVoiceSource());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.voices).toEqual([]);
      expect(result.current.error).toEqual(mockError);
    });

    it("should handle unexpected exception in fetchVoices", async () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);
      fetchVoicesMock.mockRejectedValue(new Error("Unexpected crash"));

      const { result } = renderHook(() => useVoiceSource());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.voices).toEqual([]);
      expect(result.current.error).toEqual({
        code: "hook_unexpected_error",
        detail: "Unexpected crash",
      });
    });

    it("should handle non-Error thrown value", async () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);
      fetchVoicesMock.mockRejectedValue("string exception");

      const { result } = renderHook(() => useVoiceSource());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toEqual({
        code: "hook_unexpected_error",
        detail: "string exception",
      });
    });
  });

  describe("with autoFetch=false", () => {
    it("should NOT fetch on mount when autoFetch is false", () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);

      renderHook(() => useVoiceSource({ autoFetch: false }));

      // 同步断言：fetchVoices 不应该在渲染期间立即被调用
      expect(fetchVoicesMock).not.toHaveBeenCalled();
    });

    it("should have correct initial state with autoFetch=false", () => {
      const { result } = renderHook(() =>
        useVoiceSource({ autoFetch: false }),
      );

      expect(result.current.loading).toBe(false);
      expect(result.current.voices).toEqual([]);
      expect(result.current.error).toBeNull();
    });
  });

  describe("refresh() method", () => {
    it("should re-fetch voices and update state on success", async () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);
      fetchVoicesMock.mockResolvedValueOnce({
        ok: true,
        data: mockVoices.slice(0, 1), // 第一次返回 1 个
      });

      const { result } = renderHook(() =>
        useVoiceSource({ autoFetch: false }),
      );

      // 手动调用 refresh
      await act(async () => {
        await result.current.refresh();
      });

      expect(fetchVoicesMock).toHaveBeenCalledTimes(1);
      expect(result.current.loading).toBe(false);
      expect(result.current.voices).toEqual(mockVoices.slice(0, 1));
      expect(result.current.error).toBeNull();

      // 模拟刷新返回更多数据
      fetchVoicesMock.mockResolvedValueOnce({
        ok: true,
        data: mockVoices,
      });

      await act(async () => {
        await result.current.refresh();
      });

      expect(fetchVoicesMock).toHaveBeenCalledTimes(2);
      expect(result.current.voices).toEqual(mockVoices);
    });

    it("should set loading to true during refresh and false after", async () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);
      type FetchVoicesResult = Awaited<ReturnType<typeof fetchVoices>>;
      let resolveFetch: (value: FetchVoicesResult | PromiseLike<FetchVoicesResult>) => void;
      fetchVoicesMock.mockImplementation(
        () =>
          new Promise<FetchVoicesResult>((resolve) => {
            resolveFetch = resolve;
          }),
      );

      const { result } = renderHook(() =>
        useVoiceSource({ autoFetch: false }),
      );

      expect(result.current.loading).toBe(false);

      let refreshPromise: Promise<void>;
      act(() => {
        refreshPromise = result.current.refresh();
      });

      // 刷新过程中 loading 应为 true
      await waitFor(() => {
        expect(result.current.loading).toBe(true);
      });

      // resolve fetch
      act(() => {
        resolveFetch!({ ok: true, data: mockVoices });
      });

      await act(async () => {
        await refreshPromise!;
      });

      expect(result.current.loading).toBe(false);
      expect(result.current.voices).toEqual(mockVoices);
    });

    it("should clear previous error before new fetch", async () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);

      // 第一次返回错误
      fetchVoicesMock.mockResolvedValueOnce({
        ok: false,
        error: { code: "err1", detail: "First error" },
      });

      const { result } = renderHook(() =>
        useVoiceSource({ autoFetch: false }),
      );

      // 触发第一个 refresh 得到错误
      await act(async () => {
        await result.current.refresh();
      });

      expect(result.current.error).toEqual({
        code: "err1",
        detail: "First error",
      });

      // 准备第二个 refresh：模拟 pending 状态
      type FetchVoicesResult = Awaited<ReturnType<typeof fetchVoices>>;
      let resolveFetch: (value: FetchVoicesResult | PromiseLike<FetchVoicesResult>) => void;
      const pendingPromise = new Promise<FetchVoicesResult>((resolve) => {
        resolveFetch = resolve;
      });
      fetchVoicesMock.mockImplementationOnce(() => pendingPromise);

      // 启动 refresh，但不等待它完成
      let refreshPromise: Promise<void>;
      act(() => {
        refreshPromise = result.current.refresh();
      });

      // setError(null) 是同步调用的，在调用 refresh 后立即检查
      await waitFor(() => {
        expect(result.current.error).toBeNull();
      });
      // 同时 loading 应为 true
      expect(result.current.loading).toBe(true);

      // 现在 resolve fetch，让 refresh 完成
      await act(async () => {
        resolveFetch!({ ok: true, data: mockVoices });
        await refreshPromise!;
      });

      expect(result.current.error).toBeNull();
      expect(result.current.voices).toEqual(mockVoices);
      expect(result.current.loading).toBe(false);
    });

    it("should clear voices and set error when refresh fails", async () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);

      // 先成功加载
      fetchVoicesMock.mockResolvedValueOnce({
        ok: true,
        data: mockVoices,
      });

      const { result } = renderHook(() =>
        useVoiceSource({ autoFetch: false }),
      );

      await act(async () => {
        await result.current.refresh();
      });
      expect(result.current.voices).toEqual(mockVoices);

      // 然后失败
      fetchVoicesMock.mockResolvedValueOnce({
        ok: false,
        error: { code: "refresh_err", detail: "Refresh failed" },
      });

      await act(async () => {
        await result.current.refresh();
      });

      expect(result.current.voices).toEqual([]);
      expect(result.current.error).toEqual({
        code: "refresh_err",
        detail: "Refresh failed",
      });
    });
  });

  describe("refresh function stability", () => {
    it("should return stable refresh function across renders", async () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);
      fetchVoicesMock.mockResolvedValue({
        ok: true,
        data: [],
      });

      const { result, rerender } = renderHook(() => useVoiceSource());

      const firstRefresh = result.current.refresh;

      rerender();

      const secondRefresh = result.current.refresh;

      expect(firstRefresh).toBe(secondRefresh);
    });
  });

  describe("autoFetch dependency changes", () => {
    it("should fetch when autoFetch changes from false to true", async () => {
      const fetchVoicesMock = vi.mocked(fetchVoices);
      fetchVoicesMock.mockResolvedValue({
        ok: true,
        data: mockVoices,
      });

      const { result, rerender } = renderHook(
        ({ autoFetch }) => useVoiceSource({ autoFetch }),
        { initialProps: { autoFetch: false } },
      );

      // 初始状态：autoFetch=false 不调用
      expect(fetchVoicesMock).not.toHaveBeenCalled();
      expect(result.current.voices).toEqual([]);

      // 改为 autoFetch=true，应该触发 fetch
      rerender({ autoFetch: true });

      // 直接等待最终状态（voices 填充完成），避免与初始 loading=false 竞态
      await waitFor(() => {
        expect(result.current.voices).toEqual(mockVoices);
      });

      expect(fetchVoicesMock).toHaveBeenCalledTimes(1);
      expect(result.current.error).toBeNull();
      expect(result.current.loading).toBe(false);
    });
  });
});
