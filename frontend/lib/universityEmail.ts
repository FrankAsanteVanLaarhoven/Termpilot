/** Fast client check. The API is the source of truth for campus domains. */

const CONSUMER = new Set([
  "gmail.com",
  "googlemail.com",
  "yahoo.com",
  "yahoo.co.uk",
  "hotmail.com",
  "hotmail.co.uk",
  "outlook.com",
  "outlook.co.uk",
  "live.com",
  "live.co.uk",
  "icloud.com",
  "me.com",
  "proton.me",
  "protonmail.com",
  "aol.com",
  "gmx.com",
  "gmx.de",
  "mail.com",
  "yandex.com",
  "qq.com",
]);

export function universityEmailIssue(email: string): string | null {
  const value = email.trim().toLowerCase();
  if (!value || !value.includes("@") || !value.includes(".")) {
    return "Enter your university email to continue.";
  }
  const host = value.split("@")[1] ?? "";
  const labels = host.split(".").filter(Boolean);
  const parents = labels.map((_, index) => labels.slice(index).join("."));
  if (parents.some((item) => CONSUMER.has(item))) {
    return "Use your university email, not a personal Gmail or Outlook address.";
  }
  return null;
}
