import { beforeEach, describe, expect, it } from "vitest";

import type { Voice } from "@/lib/pptSpeech";
import { loadRecentVoices, pushRecentVoice } from "@/lib/recentVoices";

function voice(shortName: string): Voice {
  return {
    ShortName: shortName,
    FriendlyName: shortName,
    Locale: "en-US",
    Gender: "Female",
  };
}

describe("recentVoices", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("keeps last 5 and de-duplicates", () => {
    pushRecentVoice(voice("v1"));
    pushRecentVoice(voice("v2"));
    pushRecentVoice(voice("v3"));
    pushRecentVoice(voice("v4"));
    pushRecentVoice(voice("v5"));
    pushRecentVoice(voice("v6"));
    pushRecentVoice(voice("v4"));

    const list = loadRecentVoices().map((v) => v.shortName);
    expect(list.length).toBe(5);
    expect(list[0]).toBe("v4");
    expect(list.includes("v1")).toBe(false);
  });
});

