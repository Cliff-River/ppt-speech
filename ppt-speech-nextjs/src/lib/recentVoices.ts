import type { Voice } from "@/lib/pptSpeech";
import { readJson, writeJson } from "@/lib/storage";

export type RecentVoice = {
  shortName: string;
  friendlyName: string;
  locale?: string;
  gender?: string;
};

const STORAGE_KEY = "ppt-speech.recentVoices.v1";
const LIMIT = 5;

export function loadRecentVoices(): RecentVoice[] {
  return readJson<RecentVoice[]>(STORAGE_KEY, []);
}

export function pushRecentVoice(voice: Voice) {
  const next: RecentVoice = {
    shortName: voice.ShortName,
    friendlyName: voice.FriendlyName ?? voice.ShortName,
    locale: voice.Locale,
    gender: voice.Gender,
  };

  const current = loadRecentVoices();
  const deduped = [next, ...current.filter((v) => v.shortName !== next.shortName)];
  writeJson(STORAGE_KEY, deduped.slice(0, LIMIT));
}

