"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { RTL, isLocale, t, type Locale } from "@/lib/i18n";
import {
  TIMEZONES,
  bcp47,
  isRegion,
  packFor,
  type Formality,
  type RegionCode,
  type UiMode,
} from "@/lib/localeRegistry";

type Theme = "dark" | "light" | "system";

type Ctx = {
  locale: Locale;
  setLocale: (l: Locale) => void;
  region: RegionCode;
  setRegion: (r: RegionCode) => void;
  timezone: string;
  setTimezone: (z: string) => void;
  formality: Formality;
  setFormality: (f: Formality) => void;
  uiMode: UiMode;
  setUiMode: (m: UiMode) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
  resolved: "dark" | "light";
  tr: (key: string) => string;
  tag: string;
};

const I18n = createContext<Ctx | null>(null);

export function Providers({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  const [region, setRegionState] = useState<RegionCode>("GB");
  const [timezone, setTimezoneState] = useState("Europe/London");
  const [formality, setFormalityState] = useState<Formality>("conversational");
  const [uiMode, setUiModeState] = useState<UiMode>("student");
  const [theme, setThemeState] = useState<Theme>("dark");
  const [systemDark, setSystemDark] = useState(true);

  useEffect(() => {
    const savedL = window.localStorage.getItem("tp-locale");
    const savedT = window.localStorage.getItem("tp-theme");
    const savedR = window.localStorage.getItem("tp-region");
    const savedZ = window.localStorage.getItem("tp-timezone");
    const savedF = window.localStorage.getItem("tp-formality");
    const savedM = window.localStorage.getItem("tp-ui-mode");
    if (savedL && isLocale(savedL)) setLocaleState(savedL);
    if (savedR && isRegion(savedR)) setRegionState(savedR);
    if (savedZ && (TIMEZONES as readonly string[]).includes(savedZ)) setTimezoneState(savedZ);
    if (savedF === "conversational" || savedF === "neutral" || savedF === "formal") setFormalityState(savedF);
    if (savedM === "student" || savedM === "proof") setUiModeState(savedM);
    if (savedT === "dark" || savedT === "light" || savedT === "system") setThemeState(savedT);
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    setSystemDark(mq.matches);
    const onChange = () => setSystemDark(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const resolved: "dark" | "light" = theme === "system" ? (systemDark ? "dark" : "light") : theme;
  const tag = bcp47(locale, region);

  useEffect(() => {
    document.documentElement.dataset.theme = resolved;
    document.documentElement.lang = tag;
    document.documentElement.dir = RTL.has(locale) ? "rtl" : "ltr";
    document.documentElement.dataset.mode = uiMode;
  }, [resolved, locale, tag, uiMode]);

  const value = useMemo<Ctx>(
    () => ({
      locale,
      setLocale: (l) => {
        setLocaleState(l);
        window.localStorage.setItem("tp-locale", l);
      },
      region,
      setRegion: (r) => {
        setRegionState(r);
        window.localStorage.setItem("tp-region", r);
      },
      timezone,
      setTimezone: (z) => {
        setTimezoneState(z);
        window.localStorage.setItem("tp-timezone", z);
      },
      formality,
      setFormality: (f) => {
        setFormalityState(f);
        window.localStorage.setItem("tp-formality", f);
      },
      uiMode,
      setUiMode: (m) => {
        setUiModeState(m);
        window.localStorage.setItem("tp-ui-mode", m);
      },
      theme,
      setTheme: (next) => {
        setThemeState(next);
        window.localStorage.setItem("tp-theme", next);
      },
      resolved,
      tr: (key) => t(locale, key),
      tag,
    }),
    [locale, region, timezone, formality, uiMode, theme, resolved, tag],
  );

  return <I18n.Provider value={value}>{children}</I18n.Provider>;
}

export function useI18n(): Ctx {
  const ctx = useContext(I18n);
  if (!ctx) {
    return {
      locale: "en",
      setLocale: () => undefined,
      region: "GB",
      setRegion: () => undefined,
      timezone: "Europe/London",
      setTimezone: () => undefined,
      formality: "conversational",
      setFormality: () => undefined,
      uiMode: "student",
      setUiMode: () => undefined,
      theme: "dark",
      setTheme: () => undefined,
      resolved: "dark",
      tr: (key) => t("en", key),
      tag: "en-GB",
    };
  }
  return ctx;
}

export function useLocalePack() {
  const { locale } = useI18n();
  return packFor(locale);
}
