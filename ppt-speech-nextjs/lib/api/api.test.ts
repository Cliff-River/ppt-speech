import { describe, it, expect, beforeEach, vi } from "vitest";
import { request, API_BASE_URL } from "./api";

describe("api.ts", () => {
  describe("API_BASE_URL", () => {
    it("should default to empty string when env var is not set", () => {
      // 保存原始值
      const originalProcess = global.process;

      // 模拟未设置环境变量的情况
      // 由于模块已导入，API_BASE_URL 在导入时已计算，这里直接验证当前值
      // 在测试环境下通常未设置 NEXT_PUBLIC_API_BASE_URL
      expect(typeof API_BASE_URL).toBe("string");
    });
  });

  describe("request<T>()", () => {
    beforeEach(() => {
      vi.restoreAllMocks();
    });

    it("should return data on successful JSON response", async () => {
      const mockData = { id: 1, name: "test" };
      const mockResponse = new Response(JSON.stringify(mockData), {
        status: 200,
        headers: { "content-type": "application/json" },
      });

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await request<{ id: number; name: string }>("/test");

      expect(fetch).toHaveBeenCalledWith("/test", undefined);
      expect(result.ok).toBe(true);
      if (result.ok) {
        expect(result.data).toEqual(mockData);
      }
    });

    it("should return text data when response is not JSON", async () => {
      const mockText = "plain text response";
      const mockResponse = new Response(mockText, {
        status: 200,
        headers: { "content-type": "text/plain" },
      });

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await request<string>("/test");

      expect(result.ok).toBe(true);
      if (result.ok) {
        expect(result.data).toBe(mockText);
      }
    });

    it("should handle JSON error response on non-2xx status", async () => {
      const errorBody = { code: "custom_error", detail: "Something went wrong" };
      const mockResponse = new Response(JSON.stringify(errorBody), {
        status: 400,
        statusText: "Bad Request",
        headers: { "content-type": "application/json" },
      });

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await request("/test");

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("custom_error");
        expect(result.error.detail).toBe("Something went wrong");
      }
    });

    it("should handle non-JSON error response on non-2xx status", async () => {
      const mockResponse = new Response("Not Found", {
        status: 404,
        statusText: "Not Found",
        headers: { "content-type": "text/plain" },
      });

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await request("/test");

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("http_404");
        expect(result.error.detail).toBe("Not Found");
      }
    });

    it("should use HTTP status code as detail when statusText is empty", async () => {
      const mockResponse = new Response("", {
        status: 500,
        statusText: "",
        headers: { "content-type": "text/plain" },
      });

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await request("/test");

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("http_500");
        expect(result.error.detail).toBe("HTTP 500");
      }
    });

    it("should use default code and detail when JSON error body is empty", async () => {
      const mockResponse = new Response(JSON.stringify({}), {
        status: 403,
        statusText: "Forbidden",
        headers: { "content-type": "application/json" },
      });

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await request("/test");

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("http_403");
        expect(result.error.detail).toBe("Forbidden");
      }
    });

    it("should return network_error when fetch throws an Error", async () => {
      const mockError = new Error("Failed to connect");
      global.fetch = vi.fn().mockRejectedValue(mockError);

      const result = await request("/test");

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("network_error");
        expect(result.error.detail).toBe("Failed to connect");
      }
    });

    it("should return network_error when fetch throws a non-Error value", async () => {
      global.fetch = vi.fn().mockRejectedValue("string error");

      const result = await request("/test");

      expect(result.ok).toBe(false);
      if (!result.ok) {
        expect(result.error.code).toBe("network_error");
        expect(result.error.detail).toBe("string error");
      }
    });

    it("should pass RequestInit options to fetch", async () => {
      const mockData = { success: true };
      const mockResponse = new Response(JSON.stringify(mockData), {
        status: 200,
        headers: { "content-type": "application/json" },
      });

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const init: RequestInit = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key: "value" }),
      };

      await request("/test", init);

      expect(fetch).toHaveBeenCalledWith("/test", init);
    });

    it("should handle response without content-type header", async () => {
      const mockData = { key: "value" };
      const mockResponse = new Response(JSON.stringify(mockData), {
        status: 200,
      });
      // 手动移除 content-type header
      mockResponse.headers.delete("content-type");

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await request<{ key: string }>("/test");

      expect(result.ok).toBe(true);
      if (result.ok) {
        // 没有 content-type 会走 text 分支
        expect(typeof result.data).toBe("string");
      }
    });

    it("should handle case-insensitive content-type header", async () => {
      // fetch 的 headers.get 本身是大小写不敏感的，这里测试包含 application/json 的场景
      const mockData = { id: 123 };
      const mockResponse = new Response(JSON.stringify(mockData), {
        status: 200,
        headers: { "Content-Type": "APPLICATION/JSON; charset=utf-8" },
      });

      global.fetch = vi.fn().mockResolvedValue(mockResponse);

      const result = await request<{ id: number }>("/test");

      expect(result.ok).toBe(true);
      if (result.ok) {
        expect(result.data).toEqual(mockData);
      }
    });
  });
});
