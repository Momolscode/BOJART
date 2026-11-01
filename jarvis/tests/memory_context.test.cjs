const assert = require("node:assert/strict");
const test = require("node:test");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname, "../apps/jarvis/app/memory.js"), "utf8");

class Element {
  constructor() { this.value = ""; this.children = []; this._text = ""; this.disabled = false; }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() { return this._text + this.children.map(e => e.textContent).join(""); }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this._text = ""; this.children = items; }
}
const tick = () => new Promise(resolve => setImmediate(resolve));
const status = {sources: 2, agent_episodes: 0, database_integrity: "ok", chat_configured: false};
const fact = value => ({key: value, value, status: "proposal", observed_at: "fixture", source: "test"});
const search = value => ({results: [{source_path: "test.md", start_line: 1, end_line: 1, text: value, citation: "test"}], semantic_status: "disabled"});

async function harness() {
  const nodes = new Map(), requests = [];
  const get = id => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
  get("domain").value = "bojart.jarvis";
  get("question").value = "Question";
  vm.runInNewContext(source, {
    document: {getElementById: get, createElement: () => new Element()},
    localStorage: {getItem: () => "test-session", setItem() {}},
    crypto: {randomUUID: () => "test-request"},
    navigator: {clipboard: {writeText: async () => {}}},
    fetch: (url, options) => new Promise(resolve => requests.push({
      url, options, respond: data => resolve({ok: true, json: async () => data})
    }))
  });
  function reply(prefix, data) {
    const i = requests.findIndex(r => r.url.startsWith(prefix));
    assert.notEqual(i, -1, "Pending request: " + prefix);
    requests.splice(i, 1)[0].respond(data);
  }
  reply("/api/memory/status", status); await tick();
  reply("/api/memory/facts", {facts: []}); await tick();
  return {get, reply, requests};
}

test("changing domain clears results immediately and ignores a late search", async () => {
  const h = await harness();
  h.get("results").textContent = "OLD_CONTEXT";
  const pending = h.get("search").onclick();
  h.get("domain").value = "bojart.creative";
  const changed = h.get("domain").onchange();
  assert.doesNotMatch(h.get("results").textContent, /OLD_CONTEXT/);
  h.reply("/api/memory/status", status); await tick();
  h.reply("/api/memory/facts", {facts: [fact("CREATIVE")]}); await changed;
  h.reply("/api/memory/recall", search("LATE_JARVIS")); await pending;
  assert.doesNotMatch(h.get("results").textContent, /LATE_JARVIS/);
  assert.match(h.get("fact-list").textContent, /CREATIVE/);
});

test("late facts cannot replace the facts of a newer domain", async () => {
  const h = await harness();
  h.get("domain").value = "bojart.creative";
  const first = h.get("domain").onchange();
  h.reply("/api/memory/status", status); await tick();
  h.get("domain").value = "bojart.sites";
  const second = h.get("domain").onchange();
  h.reply("/api/memory/status", status); await tick();
  h.reply("/api/memory/facts?project=bojart.sites", {facts: [fact("SITES")]}); await second;
  h.reply("/api/memory/facts?project=bojart.creative", {facts: [fact("OLD_CREATIVE")]}); await first;
  assert.match(h.get("fact-list").textContent, /SITES/);
  assert.doesNotMatch(h.get("fact-list").textContent, /OLD_CREATIVE/);
});

test("an earlier context response cannot replace a newer search", async () => {
  const h = await harness();
  const first = h.get("context").onclick();
  const second = h.get("search").onclick();
  h.reply("/api/memory/recall", search("NEW_SEARCH")); await second;
  h.reply("/api/memory/context", {text: "OLD_PACK", characters: 8, citations: [], omitted: 0}); await first;
  assert.match(h.get("results").textContent, /NEW_SEARCH/);
  assert.doesNotMatch(h.get("results").textContent, /OLD_PACK/);
});

test("a late model answer cannot reappear after switching domain", async () => {
  const h = await harness();
  const answer = h.get("ask").onclick();
  h.get("domain").value = "bojart.creative";
  const changed = h.get("domain").onchange();
  h.reply("/api/memory/status", status); await tick();
  h.reply("/api/memory/facts", {facts: []}); await changed;
  h.reply("/api/memory/ask", {answer: "OLD_ANSWER", context_sha256: "test"});
  // The old implementation refreshes after displaying the stale answer.
  await tick();
  if (h.requests.some(r => r.url === "/api/memory/status")) {
    h.reply("/api/memory/status", status); await tick();
    h.reply("/api/memory/facts", {facts: []});
  }
  await answer;
  assert.doesNotMatch(h.get("results").textContent, /OLD_ANSWER/);
});
