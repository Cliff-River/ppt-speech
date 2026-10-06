import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Voice } from "@/lib/types/voice";
import { useVoicesList } from "./useVoicesList";

const mockVoices: Voice[] = [
  {
    Name: "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)",
    ShortName: "zh-CN-XiaoxiaoNeural",
    Gender: "Female",
    Locale: "zh-CN",
    SuggestedCodec: "audio-24khz-48kbitrate-mono-mp3",
    FriendlyName:
      "Microsoft Xiaoxiao Online (Natural) - Chinese (Mandarin, Simplified)",
    Status: "GA",
    VoiceTag: {
      ContentCategories: ["General", "News"],
      VoicePersonalities: ["Friendly", "Positive"],
    },
    Language: "zh",
  },
  {
    Name: "Microsoft Server Speech Text to Speech Voice (en-US, JennyNeural)",
    ShortName: "en-US-JennyNeural",
    Gender: "Female",
    Locale: "en-US",
    SuggestedCodec: "audio-24khz-48kbitrate-mono-mp3",
    FriendlyName: "Microsoft Jenny Online (Natural) - English (United States)",
    Status: "GA",
    VoiceTag: {
      ContentCategories: ["General"],
      VoicePersonalities: ["Friendly", "Conversational"],
    },
    Language: "en",
  },
  {
    Name: "Microsoft Server Speech Text to Speech Voice (en-US, GuyNeural)",
    ShortName: "en-US-GuyNeural",
    Gender: "Male",
    Locale: "en-US",
    SuggestedCodec: "audio-24khz-48kbitrate-mono-mp3",
    FriendlyName: "Microsoft Guy Online (Natural) - English (United States)",
    Status: "GA",
    VoiceTag: {
      ContentCategories: ["News"],
      VoicePersonalities: ["Professional", "Reliable"],
    },
    Language: "en",
  },
];

const shortNames = (voices: Voice[]) => voices.map((voice) => voice.ShortName);

describe("useVoicesList", () => {
  describe("initial state", () => {
    it("should return all voices and default filters on mount", () => {
      const { result } = renderHook(() => useVoicesList(mockVoices));

      expect(result.current.filteredVoices).toEqual(mockVoices);
      expect(result.current.filters).toEqual({
        keyword: "",
        gender: null,
        language: null,
        locale: null,
        category: null,
        personality: null,
      });
      expect(typeof result.current.setFilters).toBe("function");
      expect(typeof result.current.resetFilters).toBe("function");
    });

    it("should derive available filter options from the source voices", () => {
      const { result } = renderHook(() => useVoicesList(mockVoices));

      expect(result.current.availableOptions).toEqual({
        genders: ["Female", "Male"],
        languages: ["en", "zh"],
        locales: ["en-US", "zh-CN"],
        categories: ["General", "News"],
        personalities: [
          "Conversational",
          "Friendly",
          "Positive",
          "Professional",
          "Reliable",
        ],
      });
    });

    it("should handle an empty voice list", () => {
      const { result } = renderHook(() => useVoicesList([]));

      expect(result.current.filteredVoices).toEqual([]);
      expect(result.current.availableOptions.genders).toEqual([]);
    });

    it("should apply initialFilters when provided", () => {
      const { result } = renderHook(() =>
        useVoicesList(mockVoices, { initialFilters: { gender: "Male" } }),
      );

      expect(result.current.filters.gender).toBe("Male");
      expect(shortNames(result.current.filteredVoices)).toEqual([
        "en-US-GuyNeural",
      ]);
    });
  });

  describe("setFilters", () => {
    it("should update filtered results according to the new condition", () => {
      const { result } = renderHook(() => useVoicesList(mockVoices));

      act(() => {
        result.current.setFilters({ keyword: "jenny" });
      });

      expect(shortNames(result.current.filteredVoices)).toEqual([
        "en-US-JennyNeural",
      ]);
    });

    it("should merge the patch without dropping previously set conditions", () => {
      const { result } = renderHook(() => useVoicesList(mockVoices));

      act(() => {
        result.current.setFilters({ gender: "Female" });
      });
      expect(shortNames(result.current.filteredVoices)).toEqual([
        "zh-CN-XiaoxiaoNeural",
        "en-US-JennyNeural",
      ]);

      // 再设置 locale 时，gender 条件应继续生效（AND 叠加而非覆盖）
      act(() => {
        result.current.setFilters({ locale: "en-US" });
      });

      expect(result.current.filters).toMatchObject({
        gender: "Female",
        locale: "en-US",
      });
      expect(shortNames(result.current.filteredVoices)).toEqual([
        "en-US-JennyNeural",
      ]);
    });

    it("should clear a condition when it is set back to its unrestricted value", () => {
      const { result } = renderHook(() =>
        useVoicesList(mockVoices, { initialFilters: { gender: "Male" } }),
      );

      act(() => {
        result.current.setFilters({ gender: null });
      });

      expect(result.current.filters.gender).toBeNull();
      expect(result.current.filteredVoices).toEqual(mockVoices);
    });
  });

  describe("resetFilters", () => {
    it("should clear all conditions back to defaults", () => {
      const { result } = renderHook(() => useVoicesList(mockVoices));

      act(() => {
        result.current.setFilters({
          keyword: "guy",
          gender: "Male",
          locale: "en-US",
        });
      });
      expect(shortNames(result.current.filteredVoices)).toEqual([
        "en-US-GuyNeural",
      ]);

      act(() => {
        result.current.resetFilters();
      });

      expect(result.current.filters).toEqual({
        keyword: "",
        gender: null,
        language: null,
        locale: null,
        category: null,
        personality: null,
      });
      expect(result.current.filteredVoices).toEqual(mockVoices);
    });

    it("should restore the initialFilters provided at mount", () => {
      const { result } = renderHook(() =>
        useVoicesList(mockVoices, { initialFilters: { language: "zh" } }),
      );

      act(() => {
        result.current.setFilters({ language: "en", gender: "Male" });
      });
      expect(shortNames(result.current.filteredVoices)).toEqual([
        "en-US-GuyNeural",
      ]);

      act(() => {
        result.current.resetFilters();
      });

      expect(result.current.filters).toMatchObject({
        language: "zh",
        gender: null,
      });
      expect(shortNames(result.current.filteredVoices)).toEqual([
        "zh-CN-XiaoxiaoNeural",
      ]);
    });
  });

  describe("reactivity and memoization", () => {
    it("should recompute filtered voices when the voices prop changes", () => {
      const { result, rerender } = renderHook(
        ({ voices }) => useVoicesList(voices),
        { initialProps: { voices: mockVoices } },
      );

      expect(result.current.filteredVoices).toHaveLength(3);

      rerender({ voices: mockVoices.slice(0, 1) });

      expect(shortNames(result.current.filteredVoices)).toEqual([
        "zh-CN-XiaoxiaoNeural",
      ]);
    });

    it("should keep a stable filteredVoices reference across unrelated rerenders", () => {
      const { result, rerender } = renderHook(() => useVoicesList(mockVoices));

      const firstResult = result.current.filteredVoices;
      rerender();
      expect(result.current.filteredVoices).toBe(firstResult);

      act(() => {
        result.current.setFilters({ gender: "Female" });
      });
      expect(result.current.filteredVoices).not.toBe(firstResult);
    });

    it("should keep stable setFilters / resetFilters references across rerenders", () => {
      const { result, rerender } = renderHook(() => useVoicesList(mockVoices));

      const { setFilters, resetFilters } = result.current;
      rerender();

      expect(result.current.setFilters).toBe(setFilters);
      expect(result.current.resetFilters).toBe(resetFilters);
    });
  });
});
