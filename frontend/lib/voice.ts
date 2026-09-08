/** Browser speech for the landing G1. No third-party TTS key required. */

let unlocked = false;
let resumeTimer: number | null = null;

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

/** Chrome blocks speech until a click/tap. Call this from a pointer handler. */
export function unlockVoice(): void {
  if (typeof window === "undefined" || !window.speechSynthesis || unlocked) return;
  unlocked = true;
  const kick = new SpeechSynthesisUtterance(" ");
  kick.volume = 0;
  window.speechSynthesis.speak(kick);
  if (resumeTimer == null) {
    resumeTimer = window.setInterval(() => {
      if (window.speechSynthesis.speaking) window.speechSynthesis.resume();
    }, 5000);
  }
}

export function speak(
  text: string,
  onStart?: () => void,
  onEnd?: () => void,
): void {
  if (typeof window === "undefined" || !window.speechSynthesis) {
    onEnd?.();
    return;
  }
  const run = () => {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voice = pickVoice();
    if (voice) utterance.voice = voice;
    utterance.rate = 1.02;
    utterance.pitch = 1.04;
    utterance.onstart = () => onStart?.();
    utterance.onend = () => onEnd?.();
    utterance.onerror = () => onEnd?.();
    window.speechSynthesis.resume();
    window.speechSynthesis.speak(utterance);
  };
  if (window.speechSynthesis.getVoices().length) run();
  else {
    window.speechSynthesis.addEventListener("voiceschanged", run, { once: true });
    window.setTimeout(run, 250);
  }
}

export function silence(): void {
  if (typeof window === "undefined") return;
  window.speechSynthesis?.cancel();
}
