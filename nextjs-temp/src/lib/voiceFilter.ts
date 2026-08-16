import type { Voice } from "@/lib/pptSpeech";

export type VoiceFilters = {
  query: string;
  gender: string | null;
  language: string | null;
  region: string | null;
  multilingualOnly: boolean;
  style: string | null;
};

export function getLocaleLanguage(locale: string | undefined) {
  if (!locale) return "";
  return locale.split("-")[0] ?? "";
}

export function getLocaleRegion(locale: string | undefined) {
  if (!locale) return "";
  return locale.split("-")[1] ?? "";
}

export function isMultilingual(voice: Voice) {
  const name = voice.FriendlyName ?? voice.ShortName ?? "";
  if (name.toLowerCase().includes("multilingual")) return true;
  return (voice.SecondaryLocaleList?.length ?? 0) > 0;
}

export function collectStyles(voices: Voice[]) {
  const set = new Set<string>();
  for (const v of voices) {
    for (const s of v.StyleList ?? []) {
      if (s) set.add(s);
    }
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b));
}

function matchesQuery(voice: Voice, query: string) {
  if (!query) return true;
  const q = query.trim().toLowerCase();
  if (!q) return true;

  const name = (voice.FriendlyName ?? "").toLowerCase();
  const shortName = (voice.ShortName ?? "").toLowerCase();
  return name.includes(q) || shortName.includes(q);
}

export function applyVoiceFilters(voices: Voice[], filters: VoiceFilters) {
  return voices.filter((v) => {
    if (!matchesQuery(v, filters.query)) return false;

    if (filters.gender && (v.Gender ?? "") !== filters.gender) return false;

    const language = getLocaleLanguage(v.Locale);
    const region = getLocaleRegion(v.Locale);
    if (filters.language && language !== filters.language) return false;
    if (filters.region && region !== filters.region) return false;

    if (filters.multilingualOnly && !isMultilingual(v)) return false;

    if (filters.style && !(v.StyleList ?? []).includes(filters.style)) return false;

    return true;
  });
}

function priorityForLocale(locale: string | undefined) {
  const language = getLocaleLanguage(locale);
  if (language === "zh") return 0;
  if (language === "en") return 1;
  return 2;
}

export function sortVoices(voices: Voice[]) {
  return [...voices].sort((a, b) => {
    const pa = priorityForLocale(a.Locale);
    const pb = priorityForLocale(b.Locale);
    if (pa !== pb) return pa - pb;

    const la = (a.Locale ?? "").localeCompare(b.Locale ?? "");
    if (la !== 0) return la;

    const na = a.FriendlyName ?? a.ShortName ?? "";
    const nb = b.FriendlyName ?? b.ShortName ?? "";
    return na.localeCompare(nb);
  });
}

export function collectLanguages(voices: Voice[]) {
  const set = new Set<string>();
  for (const v of voices) {
    const language = getLocaleLanguage(v.Locale);
    if (language) set.add(language);
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b));
}

export function collectRegionsForLanguage(voices: Voice[], language: string | null) {
  const set = new Set<string>();
  for (const v of voices) {
    const l = getLocaleLanguage(v.Locale);
    if (language && l !== language) continue;
    const region = getLocaleRegion(v.Locale);
    if (region) set.add(region);
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b));
}

