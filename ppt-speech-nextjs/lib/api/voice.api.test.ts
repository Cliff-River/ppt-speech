import { describe, it, expect, beforeEach, vi } from "vitest";
import { fetchVoices } from "./voice.api";
import type { Voice, ApiError } from "@/lib/types/voice";

// 模拟 request 函数
vi.mock("./api", () => ({
  API_BASE_URL: "",
  request: vi.fn(),
}));

import { request } from "./api";

const mockVoices: Voice[] = [
  {
    Name: "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)",
    ShortName: "zh-CN-XiaoxiaoNeural",
    Gender: "Female",
    Locale: "zh-CN",
    SuggestedCodec: "audio-24khz-48kbitrate-mono-mp3",
    FriendlyName: "Microsoft Xiaoxiao Online (Natural) - Chinese (Mainland)",
    Status: "GA",
    VoiceTag: {
      ContentCategories: ["News", "Novel"],
      VoicePersonalities: ["Warm", "Friendly"],
    },
    Language: "Chinese (Mandarin, simplified)",
  },
  {
    Name: "Microsoft Server Speech Text to Speech Voice (en-US, JennyNeural)",
    ShortName: "en-US-JennyNeural",
    Gender: "Female",
    Locale: "en-US",
    SuggestedCodec: "audio-24khz-48kbitrate-mono-mp3",
    FriendlyName: "Microsoft Jenny Online (Natural) - English (US)",
    Status: "GA",
    VoiceTag: {
      ContentCategories: ["News", "Conversation"],
      VoicePersonalities: ["Professional", "Friendly"],
    },
    Language: "English (US)",
  },
];

describe("voice.api.ts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("fetchVoices()", () => {
    it("should call request with correct URL and options", async () => {
      const requestMock = vi.mocked(request);
      requestMock.mockResolvedValue({
        ok: true,
        data: { voices: mockVoices },
      });

      await fetchVoices();

      expect(requestMock).toHaveBeenCalledTimes(1);
      expect(requestMock).toHaveBeenCalledWith("/api/v1/voices", {
        method: "GET",
        headers: { Accept: "application/json" },
      });
    });

    it("should return voices array on successful response", async () => {
      const requestMock = vi.mocked(request);
      requestMock.mockResolvedValue({
        ok: true,
        data: { voices: mockVoices },
      });

      const result = await fetchVoices();

      expect(result.ok).toBe(true);
      if (result.ok) {
        expect(result.data).toEqual(mockVoices);
        expect(result.data).toHaveLength(2);
        expect(result.data[0].ShortName).toBe("zh-CN-XiaoxiaoNeural");
      }
    });

    it("should return empty array when voices is undefined in response", async () => {
      const requestMock = vi.mocked(request);
      requestMock.mockResolvedValue({
        ok: true,
        data: {},
      });

      const result = await fetchVoices();

      expect(result.ok).toBe(true);
      if (result.ok) {
        expect(result.data).toEqual([]);
      }
    });

    it("should return empty array when voices is null in response", async () => {
      const requestMock = vi.mocked(request);
      requestMock.mockResolvedValue({
        ok: true,
        data: { voices: null as unknown as Voice[] },
      });

      const result = await fetchVoices();

      expect(result.ok).toBe(true);
      if (result.ok) {
        expect(result.data).toEqual([]);
      }
    });

    it("should propagate error when request fails with structured error", async () => {
      const mockError: ApiError = {
        code: "server_error",
        detail: "Internal server error",
      };
      const requestMock = vi.mocked(request);
      requestMock.mockResolvedValue({
        ok: false,
        error: mockError,
      });

      const result = await fetchVoices();

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error).toEqual(mockError);
      }
    });

    it("should propagate error when request fails with HTTP error", async () => {
      const mockError: ApiError = {
        code: "http_401",
        detail: "Unauthorized",
      };
      const requestMock = vi.mocked(request);
      requestMock.mockResolvedValue({
        ok: false,
        error: mockError,
      });

      const result = await fetchVoices();

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("http_401");
        expect(result.error.detail).toBe("Unauthorized");
      }
    });

    it("should merge custom RequestInit options with defaults", async () => {
      const requestMock = vi.mocked(request);
      requestMock.mockResolvedValue({
        ok: true,
        data: { voices: [] },
      });

      const customOptions: RequestInit = {
        cache: "no-store",
        headers: { Authorization: "Bearer token" },
      };

      await fetchVoices(customOptions);

      expect(requestMock).toHaveBeenCalledWith("/api/v1/voices", {
        method: "GET",
        headers: {
          Accept: "application/json",
          Authorization: "Bearer token",
        },
        cache: "no-store",
      });
    });

    it("should allow overriding method via custom options", async () => {
      const requestMock = vi.mocked(request);
      requestMock.mockResolvedValue({
        ok: true,
        data: { voices: [] },
      });

      // 虽然语义上不应该覆盖 GET，但我们要测试自定义选项能覆盖默认值
      const customOptions: RequestInit = {
        method: "POST",
      };

      await fetchVoices(customOptions);

      expect(requestMock).toHaveBeenCalledWith("/api/v1/voices", {
        method: "POST",
        headers: { Accept: "application/json" },
      });
    });

    it("should return empty voices array when API returns empty list", async () => {
      const requestMock = vi.mocked(request);
      requestMock.mockResolvedValue({
        ok: true,
        data: { voices: [] },
      });

      const result = await fetchVoices();

      expect(result.ok).toBe(true);
      if (result.ok) {
        expect(result.data).toEqual([]);
        expect(result.data).toHaveLength(0);
      }
    });
  });
});
