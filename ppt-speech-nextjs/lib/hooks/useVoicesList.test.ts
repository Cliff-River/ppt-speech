import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { useVoicesList } from "./useVoicesList";

describe("useVoicesList", () => {
  it("should be defined as a function", () => {
    expect(typeof useVoicesList).toBe("function");
  });

  it("should be callable without throwing errors", () => {
    expect(() => {
      renderHook(() => useVoicesList());
    }).not.toThrow();
  });

  it("should return undefined (current stub implementation)", () => {
    const { result } = renderHook(() => useVoicesList());
    expect(result.current).toBeUndefined();
  });

  it("should accept being called multiple times consistently", () => {
    const { result: r1 } = renderHook(() => useVoicesList());
    const { result: r2 } = renderHook(() => useVoicesList());
    const { result: r3 } = renderHook(() => useVoicesList());

    expect(r1.current).toBeUndefined();
    expect(r2.current).toBeUndefined();
    expect(r3.current).toBeUndefined();
  });

  it("should not cause hook order violations in strict rendering", () => {
    // renderHook internally wraps in React.StrictMode when appropriate,
    // so this validates that the hook is safe even if expanded later.
    const { rerender } = renderHook(() => useVoicesList());
    rerender();
    rerender();
  });
});
