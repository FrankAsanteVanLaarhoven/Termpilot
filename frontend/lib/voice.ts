/** Browser speech for the landing G1. No third-party TTS key required. */

let unlocked = false;
let resumeTimer: number | null = null;
let speakGen = 0;

function pickVoice(): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;
  const score = (voice: SpeechSynthesisVoice) => {
    const name = voice.name.toLowerCase();
    const lang = voice.lang.toLowerCase();
    let n = 0;
    if (lang.startsWith("en")) n += 4;
    if (lang.includes("gb") || lang.includes("uk")) n += 2;
    if (/samantha|serena|libby|google uk|karen|moira|fiona/.test(name)) n += 3;
    return n;
  };
  return [...voices].sort((a, b) => score(b) - score(a))[0] ?? null;
}

export function voiceUnlocked(): boolean {
  return unlocked;
}

/** Mark this tab as allowed to speak. Must run inside a click/tap. */
export function unlockVoice(): void {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  unlocked = true;
  window.speechSynthesis.resume();
  if (resumeTimer == null) {
    resumeTimer = window.setInterval(() => {
      if (window.speechSynthesis.speaking) window.speechSynthesis.resume();
    }, 4000);
  }
}

export function speak(
  text: string,
  onStart?: () => void,
  onEnd?: () => void,
): void {
  const gen = ++speakGen;
  let finished = false;
  const start = () => {
    if (gen !== speakGen || finished) return;
    onStart?.();
  };
  const done = () => {
    if (gen !== speakGen || finished) return;
    finished = true;
    onEnd?.();
  };
  if (typeof window === "undefined" || !window.speechSynthesis) {
    start();
    window.setTimeout(done, Math.min(12000, Math.max(2800, text.split(/\s+/).length * 260)));
    return;
  }
  unlocked = true;
  window.speechSynthesis.resume();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-GB";
  const voice = pickVoice();
  if (voice) utterance.voice = voice;
  utterance.rate = 1.02;
  utterance.pitch = 1.04;
  utterance.onstart = start;
  utterance.onend = done;
  utterance.onerror = done;
  start();
  window.speechSynthesis.speak(utterance);
  const wait = Math.min(16000, Math.max(3200, text.split(/\s+/).length * 280));
  window.setTimeout(done, wait);
}

export function silence(): void {
  speakGen += 1;
  if (typeof window === "undefined") return;
  window.speechSynthesis?.cancel();
}
