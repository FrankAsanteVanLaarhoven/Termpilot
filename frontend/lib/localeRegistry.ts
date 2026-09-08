import type { Locale } from "@/lib/i18n";

export type UiMode = "student" | "proof";
export type Formality = "conversational" | "neutral" | "formal";

export type Maturity =
  | "grok_voice_localised"
  | "conversation_localised"
  | "interface_available"
  | "community_reviewed"
  | "fully_reviewed"
  | "voice_evaluated"
  | "limited_support";

export const GROK_VOICE_LANGS = new Set([
  "ar",
  "cs",
  "da",
  "nl",
  "en",
  "fil",
  "fr",
  "de",
  "hi",
  "id",
  "it",
  "ja",
  "ko",
  "mk",
  "ms",
  "fa",
  "pl",
  "pt",
  "ro",
  "ru",
  "es",
  "sv",
  "th",
  "tr",
  "vi",
]);

export const REGIONS = [
  { code: "GB", label: "United Kingdom", emergency: "Samaritans 116 123", tz: "Europe/London" },
  { code: "NL", label: "Netherlands", emergency: "113 Zelfmoordpreventie", tz: "Europe/Amsterdam" },
  { code: "ES", label: "Spain", emergency: "024 (mental health) · 112", tz: "Europe/Madrid" },
  { code: "SA", label: "Saudi Arabia", emergency: "997", tz: "Asia/Riyadh" },
  { code: "US", label: "United States", emergency: "988 Suicide & Crisis Lifeline", tz: "America/New_York" },
  { code: "MX", label: "Mexico", emergency: "911", tz: "America/Mexico_City" },
  { code: "NG", label: "Nigeria", emergency: "112", tz: "Africa/Lagos" },
  { code: "IN", label: "India", emergency: "112", tz: "Asia/Kolkata" },
  { code: "DE", label: "Germany", emergency: "112 · Telefonseelsorge 0800 111 0 111", tz: "Europe/Berlin" },
  { code: "FR", label: "France", emergency: "3114 · 15 / 112", tz: "Europe/Paris" },
  { code: "AE", label: "United Arab Emirates", emergency: "999", tz: "Asia/Dubai" },
  { code: "AU", label: "Australia", emergency: "Lifeline 13 11 14", tz: "Australia/Sydney" },
] as const;

export type RegionCode = (typeof REGIONS)[number]["code"];

export const TIMEZONES = [
  "Europe/London",
  "Europe/Amsterdam",
  "Europe/Madrid",
  "Europe/Berlin",
  "Europe/Paris",
  "America/New_York",
  "America/Mexico_City",
  "America/Sao_Paulo",
  "Africa/Lagos",
  "Asia/Riyadh",
  "Asia/Dubai",
  "Asia/Kolkata",
  "Asia/Shanghai",
  "Asia/Tokyo",
  "Australia/Sydney",
  "UTC",
] as const;

export type LocalePack = {
  language: Locale;
  defaultRegion: RegionCode;
  bcp47: string;
  maturity: Maturity;
  voiceEvaluated: boolean;
  rtl: boolean;
  lastVerified: string;
  limitations: string;
};

const DEFAULT_REGION: Record<string, RegionCode> = {
  en: "GB",
  es: "ES",
  nl: "NL",
  fr: "FR",
  de: "DE",
  ar: "SA",
};

export function packFor(language: Locale): LocalePack {
  const grok = GROK_VOICE_LANGS.has(language);
  const rtl = language === "ar" || language === "ur" || language === "fa";
  const region = DEFAULT_REGION[language] ?? "GB";
  return {
    language,
    defaultRegion: region,
    bcp47: `${language}-${region}`,
    maturity: grok ? "grok_voice_localised" : "conversation_localised",
    voiceEvaluated: grok,
    rtl,
    lastVerified: "2026-09-05",
    limitations: grok
      ? "UI and conversations localised. Speech uses Grok Voice. Dates and module codes stay exact."
      : "UI and conversations localised. Outside the published Grok Voice STT list; speech may use the browser.",
  };
}

export function regionInfo(code: string): (typeof REGIONS)[number] {
  return REGIONS.find((row) => row.code === code) ?? REGIONS[0];
}

export function isRegion(code: string): code is RegionCode {
  return REGIONS.some((row) => row.code === code);
}

export function bcp47(language: Locale, region: string): string {
  return `${language}-${region}`;
}

export function maturityLabel(value: Maturity): string {
  switch (value) {
    case "grok_voice_localised":
      return "Grok Voice localised";
    case "conversation_localised":
      return "Conversations localised";
    case "voice_evaluated":
      return "Voice evaluated";
    case "interface_available":
      return "Interface available";
    case "community_reviewed":
      return "Community reviewed";
    case "fully_reviewed":
      return "Fully reviewed";
    default:
      return "Limited support";
  }
}

export const MAIL_PRIORITY_KEY: Record<string, string> = {
  p0: "mail.pri.urgent",
  p1: "mail.pri.action",
  p2: "mail.pri.useful",
  p3: "mail.pri.low",
};
