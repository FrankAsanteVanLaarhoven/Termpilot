import { describe, expect, it } from "vitest";
import { LOCALES, MESSAGES, REQUIRED_KEYS, t } from "./i18n";
import { GROK_VOICE_LANGS, bcp47, isRegion, packFor, regionInfo } from "./localeRegistry";

describe("required interface keys", () => {
  it("keeps the audited opening copy in English", () => {
    expect(MESSAGES.en["chat.hello"]).toBe("What needs your attention today?");
    expect(MESSAGES.en["chat.reviewWeek"]).toBe("Review my week");
    expect(MESSAGES.en["grokbot.name"]).toBe("Grok Bot");
    expect(MESSAGES.en["chat.safety"]).toContain("never completes assessed work");
  });

  it("has every required key in English", () => {
    for (const key of REQUIRED_KEYS) {
      expect(MESSAGES.en[key]).toBeTruthy();
    }
  });

  it("does not drop required keys when overlaying other locales", () => {
    for (const locale of LOCALES) {
      for (const key of REQUIRED_KEYS) {
        expect(t(locale, key).length).toBeGreaterThan(0);
        expect(t(locale, key)).not.toBe(key);
      }
    }
  });

  it("localises opening copy for every Grok Voice language", () => {
    for (const locale of LOCALES) {
      if (locale === "en") continue;
      if (!GROK_VOICE_LANGS.has(locale)) continue;
      expect(t(locale, "chat.hello")).not.toBe(MESSAGES.en["chat.hello"]);
      expect(t(locale, "settings.disclaimer")).not.toBe(MESSAGES.en["settings.disclaimer"]);
      expect(t(locale, "nav.student.tower")).not.toBe(MESSAGES.en["nav.student.tower"]);
    }
  });

  it("does not infer region from language", () => {
    expect(isRegion("GB")).toBe(true);
    expect(bcp47("es", "GB")).toBe("es-GB");
    expect(bcp47("ar", "GB")).toBe("ar-GB");
    expect(packFor("es").defaultRegion).toBe("ES");
    expect(regionInfo("GB").emergency).toContain("116 123");
    expect(regionInfo("US").emergency).toContain("988");
  });

  it("marks Grok Voice languages as localised for speech and conversation", () => {
    expect(packFor("en").maturity).toBe("grok_voice_localised");
    expect(packFor("th").maturity).toBe("grok_voice_localised");
    expect(packFor("ar").rtl).toBe(true);
    expect(packFor("yo").maturity).toBe("conversation_localised");
    expect(packFor("en").maturity).not.toBe("fully_reviewed");
  });
});
