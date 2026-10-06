import { describe, expect, it } from "vitest";

import type { Voice, VoiceFilters } from "@/lib/types/voice";
import {
  DEFAULT_VOICE_FILTERS,
  filterVoices,
  getVoiceFilterOptions,
} from "./voiceFilter";

/** 结构参考后端 voices.json，其中特意保留 " Novel" 带前导空格的脏数据。 */
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
    Name: "Microsoft Server Speech Text to Speech Voice (zh-CN, YunxiNeural)",
    ShortName: "zh-CN-YunxiNeural",
    Gender: "Male",
    Locale: "zh-CN",
    SuggestedCodec: "audio-24khz-48kbitrate-mono-mp3",
    FriendlyName:
      "Microsoft Yunxi Online (Natural) - Chinese (Mandarin, Simplified)",
    Status: "GA",
    VoiceTag: {
      ContentCategories: [" Novel"],
      VoicePersonalities: ["Cute", "Sunshine"],
    },
    Language: "zh",
  },
  {
    Name: "Microsoft Server Speech Text to Speech Voice (zh-HK, HiuMaanNeural)",
    ShortName: "zh-HK-HiuMaanNeural",
    Gender: "Female",
    Locale: "zh-HK",
    SuggestedCodec: "audio-24khz-48kbitrate-mono-mp3",
    FriendlyName:
      "Microsoft HiuMaan Online (Natural) - Chinese (Cantonese, Traditional)",
    Status: "GA",
    VoiceTag: {
      ContentCategories: ["Dialect"],
      VoicePersonalities: ["Casual"],
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

describe("DEFAULT_VOICE_FILTERS", () => {
  it("should not restrict any condition", () => {
    expect(DEFAULT_VOICE_FILTERS).toEqual({
      keyword: "",
      gender: null,
      language: null,
      locale: null,
      category: null,
      personality: null,
    });
  });
});

describe("filterVoices", () => {
  it("should return all voices when no condition is set", () => {
    expect(filterVoices(mockVoices, DEFAULT_VOICE_FILTERS)).toEqual(mockVoices);
  });

  it("should return an empty array for an empty source list", () => {
    expect(filterVoices([], DEFAULT_VOICE_FILTERS)).toEqual([]);
  });

  it("should not mutate the input voices array", () => {
    const snapshot = [...mockVoices];
    filterVoices(mockVoices, { ...DEFAULT_VOICE_FILTERS, gender: "Female" });
    expect(mockVoices).toEqual(snapshot);
  });

  describe("keyword", () => {
    it("should match ShortName case-insensitively", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        keyword: "XIAOXIAO",
      });
      expect(shortNames(result)).toEqual(["zh-CN-XiaoxiaoNeural"]);
    });

    it("should match FriendlyName", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        keyword: "Cantonese",
      });
      expect(shortNames(result)).toEqual(["zh-HK-HiuMaanNeural"]);
    });

    it("should match Name", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        keyword: "GuyNeural",
      });
      expect(shortNames(result)).toEqual(["en-US-GuyNeural"]);
    });

    it("should match Locale case-insensitively", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        keyword: "zh-hk",
      });
      expect(shortNames(result)).toEqual(["zh-HK-HiuMaanNeural"]);
    });

    it("should trim surrounding whitespace from the keyword", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        keyword: "  jenny  ",
      });
      expect(shortNames(result)).toEqual(["en-US-JennyNeural"]);
    });

    it("should treat a whitespace-only keyword as no restriction", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        keyword: "   ",
      });
      expect(result).toHaveLength(mockVoices.length);
    });

    it("should return an empty array when nothing matches", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        keyword: "ja-JP",
      });
      expect(result).toEqual([]);
    });
  });

  describe("gender / language / locale", () => {
    it("should filter by gender", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        gender: "Male",
      });
      expect(shortNames(result)).toEqual([
        "zh-CN-YunxiNeural",
        "en-US-GuyNeural",
      ]);
    });

    it("should filter by language code", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        language: "zh",
      });
      expect(shortNames(result)).toEqual([
        "zh-CN-XiaoxiaoNeural",
        "zh-CN-YunxiNeural",
        "zh-HK-HiuMaanNeural",
      ]);
    });

    it("should filter by locale", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        locale: "en-US",
      });
      expect(shortNames(result)).toEqual([
        "en-US-JennyNeural",
        "en-US-GuyNeural",
      ]);
    });
  });

  describe("category / personality", () => {
    it("should filter by content category", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        category: "News",
      });
      expect(shortNames(result)).toEqual([
        "zh-CN-XiaoxiaoNeural",
        "en-US-GuyNeural",
      ]);
    });

    it("should match dirty category tags after trimming whitespace", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        category: "Novel",
      });
      expect(shortNames(result)).toEqual(["zh-CN-YunxiNeural"]);
    });

    it("should filter by voice personality", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        personality: "Friendly",
      });
      expect(shortNames(result)).toEqual([
        "zh-CN-XiaoxiaoNeural",
        "en-US-JennyNeural",
      ]);
    });
  });

  describe("combined conditions (AND)", () => {
    it("should require every condition to match", () => {
      const filters: VoiceFilters = {
        keyword: "",
        gender: "Female",
        language: "zh",
        locale: "zh-CN",
        category: "News",
        personality: "Friendly",
      };
      expect(shortNames(filterVoices(mockVoices, filters))).toEqual([
        "zh-CN-XiaoxiaoNeural",
      ]);
    });

    it("should combine keyword, gender and category", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        keyword: "neural",
        gender: "Male",
        category: "News",
      });
      expect(shortNames(result)).toEqual(["en-US-GuyNeural"]);
    });

    it("should return an empty array when combined conditions conflict", () => {
      const result = filterVoices(mockVoices, {
        ...DEFAULT_VOICE_FILTERS,
        gender: "Male",
        personality: "Friendly",
      });
      expect(result).toEqual([]);
    });
  });
});

describe("getVoiceFilterOptions", () => {
  it("should derive deduplicated and sorted options from voices", () => {
    expect(getVoiceFilterOptions(mockVoices)).toEqual({
      genders: ["Female", "Male"],
      languages: ["en", "zh"],
      locales: ["en-US", "zh-CN", "zh-HK"],
      // " Novel" 与（若存在）"Novel" 归一为同一个 "Novel"
      categories: ["Dialect", "General", "News", "Novel"],
      personalities: [
        "Casual",
        "Conversational",
        "Cute",
        "Friendly",
        "Positive",
        "Professional",
        "Reliable",
        "Sunshine",
      ],
    });
  });

  it("should return empty option groups for an empty voice list", () => {
    expect(getVoiceFilterOptions([])).toEqual({
      genders: [],
      languages: [],
      locales: [],
      categories: [],
      personalities: [],
    });
  });
});
