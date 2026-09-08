/* TermPilot read-only SDK. No mail send. No calendar write. */
(function (root) {
  function TermPilot(base) {
    this.base = (base || "http://127.0.0.1:8000").replace(/\/$/, "");
  }
  TermPilot.prototype.get = async function (path) {
    const r = await fetch(this.base + path);
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  };
  TermPilot.prototype.health = function () { return this.get("/health"); };
  TermPilot.prototype.tower = function () { return this.get("/tower"); };
  TermPilot.prototype.catalog = function () { return this.get("/llm/catalog"); };
  root.TermPilot = TermPilot;
})(typeof window !== "undefined" ? window : globalThis);
