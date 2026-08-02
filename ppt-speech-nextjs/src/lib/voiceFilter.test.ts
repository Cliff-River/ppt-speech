import { describe, expect, it } from "vitest";

import type { Voice } from "@/lib/pptSpeech";
import {
  applyVoiceFilters,
  collectRegionsForLanguage,
  collectStyles,
  isMultilingual,
  sortVoices,
} from "@/lib/voiceFilter";

function v(partial: Partial<Voice> & { ShortName: string }): Voice {
  return {
    ShortName: partial.ShortName,
    FriendlyName: partial.FriendlyName,
    Locale: partial.Locale,
    Gender: partial.Gender,
    StyleList: partial.StyleList,
    SecondaryLocaleList: partial.SecondaryLocaleList,
    Name: partial.Name,
    Status: partial.Status,
    VoiceTag: partial.VoiceTag,
  };
}

describe("voiceFilter", () => {
  it("sortVoices puts zh first, en second", () => {
    const voices = [
      v({ ShortName: "fr-FR-A", Locale: "fr-FR", FriendlyName: "French A" }),
      v({ ShortName: "en-US-A", Locale: "en-US", FriendlyName: "English A" }),
      v({ ShortName: "zh-CN-A", Locale: "zh-CN", FriendlyName: "Chinese A" }),
      v({ ShortName: "en-GB-B", Locale: "en-GB", FriendlyName: "English B" }),
    ];

    const sorted = sortVoices(voices).map((x) => x.ShortName);
    expect(sorted[0]).toBe("zh-CN-A");
    expect(sorted[1]).toBe("en-GB-B");
    expect(sorted[2]).toBe("en-US-A");
  });

  it("applyVoiceFilters supports query + gender + language/region", () => {
    const voices = [
      v({
        ShortName: "zh-CN-XiaoxiaoNeural",
        FriendlyName: "Xiaoxiao",
        Locale: "zh-CN",
        Gender: "Female",
      }),
      v({
        ShortName: "zh-TW-XiaozhenNeural",
        FriendlyName: "Xiaozhen",
        Locale: "zh-TW",
        Gender: "Female",
      }),
      v({
        ShortName: "en-US-AriaNeural",
        FriendlyName: "Aria",
        Locale: "en-US",
        Gender: "Female",
      }),
    ];

    const filtered = applyVoiceFilters(voices, {
      query: "xiao",
      gender: "Female",
      language: "zh",
      region: "CN",
      multilingualOnly: false,
      style: null,
    });

    expect(filtered.map((x) => x.ShortName)).toEqual(["zh-CN-XiaoxiaoNeural"]);
  });

  it("isMultilingual matches FriendlyName and SecondaryLocaleList", () => {
    expect(
      isMultilingual(
        v({
          ShortName: "en-US-A",
          FriendlyName: "English Multilingual Voice",
          Locale: "en-US",
        }),
      ),
    ).toBe(true);

    expect(
      isMultilingual(
        v({
          ShortName: "en-US-B",
          FriendlyName: "English Voice",
          Locale: "en-US",
          SecondaryLocaleList: ["fr-FR"],
        }),
      ),
    ).toBe(true);
  });

  it("collectStyles and collectRegionsForLanguage dedupe and sort", () => {
    const voices = [
      v({ ShortName: "a", Locale: "en-US", StyleList: ["chat", "newscast"] }),
      v({ ShortName: "b", Locale: "en-GB", StyleList: ["chat"] }),
      v({ ShortName: "c", Locale: "fr-FR", StyleList: [] }),
    ];

    expect(collectStyles(voices)).toEqual(["chat", "newscast"]);
    expect(collectRegionsForLanguage(voices, "en")).toEqual(["GB", "US"]);
  });
});

