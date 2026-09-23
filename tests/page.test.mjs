// Behaviour tests for the built page (tracker.html), run in jsdom against the fake cloud database.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { JSDOM } from "jsdom";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const html = fs.readFileSync(path.join(root, "tracker.html"), "utf8");
const fakeDb = fs.readFileSync(path.join(root, "tests", "fake_db.js"), "utf8");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const plain = (o) => JSON.parse(JSON.stringify(o)); // values from the jsdom realm have foreign prototypes
const SETTLE = 150; // db resolves, first snapshots (30 ms), render
const FLUSH = 500;  // the page coalesces writes for 350 ms

async function load({ seed, noDb } = {}) {
  const dom = new JSDOM("<!doctype html><html><head></head><body>" + html + "</body></html>", {
    url: "http://localhost/",
    runScripts: "dangerously",
    pretendToBeVisual: true,
    beforeParse(window) {
      window.HTMLElement.prototype.scrollIntoView = function () {};
      window.HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
      window.HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); this.dispatchEvent(new window.Event("close")); };
      window.scrollTo = () => {};
      if (seed) window.__seed = seed;
      if (!noDb) window.eval(fakeDb);
    },
  });
  await sleep(SETTLE);
  const w = dom.window;
  const d = w.document;
  const api = {
    w, d,
    $: (sel) => d.querySelector(sel),
    $$: (sel) => [...d.querySelectorAll(sel)],
    id: (i) => d.getElementById(i),
    count: () => d.getElementById("count-blu").textContent,
    countBst: () => d.getElementById("count-bst").textContent,
    box: (entryId) => d.querySelector('.entry[data-id="' + entryId + '"] input'),
    boxes: (entryId) => [...d.querySelectorAll('.entry[data-id="' + entryId + '"] input')],
    names: () => [...d.querySelectorAll(".entry label.name")].map((l) => l.firstChild.textContent.trim()),
    groups: () => [...d.querySelectorAll(".group[data-gkey]")].map((g) => ({
      title: g.querySelector("h2").textContent.trim(), meta: g.querySelector(".meta").textContent,
      done: !!g.querySelector(".done-badge"), collapsed: g.classList.contains("collapsed"), rows: g.querySelectorAll(".entry").length,
    })),
    set: async (toggleId, on) => { const el = d.getElementById(toggleId); if (el.checked !== on) { el.click(); await sleep(10); } },
    input: async (inputId, value) => { const el = d.getElementById(inputId); el.value = value; el.dispatchEvent(new w.Event("input", { bubbles: true })); await sleep(10); },
    confirm: async () => { d.getElementById("confirmForm").dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true })); await sleep(10); },
    cancel: async () => { d.getElementById("confirmCancel").click(); await sleep(10); },
    dialogOpen: () => d.getElementById("confirmDialog").hasAttribute("open"),
    writes: (p) => w.__writes.filter((x) => !p || x.path === p),
    errors: () => w.__errors,
  };
  return api;
}

test("renders the cloud snapshot and reports cloud saving", async () => {
  const p = await load();
  assert.equal(p.count(), "1 / 124");
  assert.equal(p.box(17).checked, true);
  assert.equal(p.id("syncStatus").textContent, "Saved to the cloud");
  assert.deepEqual(plain(p.errors()), []);
});

test("works without the cloud, saving on the device only", async () => {
  const p = await load({ noDb: true });
  assert.equal(p.count(), "0 / 124");
  assert.match(p.id("syncStatus").textContent, /this device only/);
});

test("a check after a frozen snapshot is applied and written once", async () => {
  const p = await load();
  p.box(2).click(); await sleep(10);
  assert.equal(p.dialogOpen(), true);
  assert.equal(p.count(), "1 / 124", "nothing changes before confirmation");
  await p.confirm();
  assert.equal(p.box(2).checked, true);
  assert.equal(p.count(), "2 / 124");
  await sleep(FLUSH);
  const writes = p.writes("progress/c1-blu");
  assert.equal(writes.length, 1);
  assert.deepEqual(plain(writes[0].data.done), { 2: true, 17: true });
  assert.deepEqual(plain(p.errors()), []);
});

test("cancelling the confirmation reverts the box and writes nothing", async () => {
  const p = await load();
  p.box(2).click(); await sleep(10);
  await p.cancel();
  assert.equal(p.box(2).checked, false);
  assert.equal(p.count(), "1 / 124");
  await sleep(FLUSH);
  assert.equal(p.writes("progress/c1-blu").length, 0);
});

test("a name tap toggles the one entry and every location copy follows", async () => {
  const p = await load();
  await p.input("levelInput", "19");
  await p.set("groupByLoc", true);
  assert.equal(p.boxes(17).length, 5, "Blood Drain appears in five locations at level 19");
  p.$$('.entry[data-id="17"] label.name')[1].click(); await sleep(10);
  assert.equal(p.dialogOpen(), true);
  await p.confirm();
  assert.deepEqual(p.boxes(17).map((b) => b.checked), [false, false, false, false, false]);
  assert.equal(p.count(), "0 / 124");
});

test("search only matches sources that count under the current filters", async () => {
  const p = await load();
  await p.set("openWorldOnly", true);
  await p.input("searchInput", "Haukke");
  assert.deepEqual(p.names(), [], "a dungeon source does not count under open world only");
  await p.set("openWorldOnly", false);
  assert.ok(p.names().includes("Ice Spikes"));
  await p.input("levelInput", "5");
  await p.input("searchInput", "Cave Bat");
  assert.deepEqual(p.names(), [], "Cave Bat is level 7, above the filter");
  await p.input("levelInput", "7");
  assert.deepEqual(p.names(), ["Blood Drain"]);
});

test("the level box counts what is obtainable at that level and turns green when complete", async () => {
  const p = await load();
  await p.input("levelInput", "12");
  assert.equal(p.id("lvlBox").textContent.trim(), "Level ≤ 12: 1 of 15 obtained");
  assert.equal(p.id("cbLevel").textContent, "≤12: 1/15");
  for (;;) { const b = p.$$(".entry input").find((x) => !x.checked); if (!b) break; b.click(); await sleep(5); await p.confirm(); } // re-query: each confirm re-renders
  assert.match(p.id("lvlBox").textContent, /15 of 15 obtained · Done ✓/);
  assert.ok(p.id("cbLevel").classList.contains("complete"));
  await p.input("levelInput", "");
  assert.equal(p.id("lvlBox").hidden, true);
});

test("grouped view: no instance groups under open world only, also-in lines, completion badges, fold defaults", async () => {
  const p = await load();
  await p.set("groupByLoc", true);
  const g = p.groups();
  const sastasha = g.find((x) => x.title === "Sastasha");
  assert.ok(sastasha && sastasha.done && sastasha.collapsed, "a fully obtained location starts folded");
  assert.ok(g.find((x) => x.title === "Central Shroud" && !x.collapsed), "an incomplete location starts open");
  await p.set("openWorldOnly", true);
  assert.ok(!p.groups().some((x) => x.title === "Haukke Manor"), "dungeon groups are left out");
  const central = p.$$(".group").find((s) => s.querySelector("h2").textContent === "Central Shroud");
  const also = central.querySelector('.entry[data-id="17"] .also').textContent;
  assert.match(also, /^Also in Lower La Noscea \(open world, Lv 7\)/);
  assert.match(central.querySelector(".meta").textContent, /\d+ of \d+ obtained/);
});

test("uncheck-all needs the word reset, and undo restores the previous set", async () => {
  const p = await load();
  p.id("clearBtn").click(); await sleep(10);
  const dlg = p.id("clearDialog");
  assert.ok(dlg.hasAttribute("open"));
  await p.input("clearInput", "rest");
  assert.equal(p.id("clearConfirm").disabled, true);
  await p.input("clearInput", " ReSeT ");
  assert.equal(p.id("clearConfirm").disabled, false);
  p.id("clearForm").dispatchEvent(new p.w.Event("submit", { bubbles: true, cancelable: true })); await sleep(10);
  assert.equal(p.count(), "0 / 124");
  assert.equal(p.id("undoBtn").hidden, false);
  await sleep(FLUSH); // let the clear reach the cloud before undoing, or the two writes coalesce
  p.id("undoBtn").click(); await sleep(10);
  assert.equal(p.count(), "1 / 124");
  await sleep(FLUSH);
  const bodies = p.writes("progress/c1-blu").map((x) => x.data.done);
  assert.deepEqual(plain(bodies), [{}, { 17: true }]);
});

test("changes made on another device are adopted; typing in the search box never writes", async () => {
  const p = await load();
  await p.w.__db.doc("settings/ui").set({ char: "c2", list: "bst", hideDone: true, openWorldOnly: false, rareCounts: false, groupByLoc: true, levels: { "c2-bst": 33 } });
  await sleep(20);
  assert.equal(p.id("char-c2").getAttribute("aria-selected"), "true");
  assert.equal(p.id("tab-bst").getAttribute("aria-selected"), "true");
  assert.equal(p.id("hideDone").checked, true);
  assert.equal(p.id("levelInput").value, "33");
  await p.w.__db.doc("settings/chars").set({ c1: "Main", c2: "Alt" });
  await sleep(20);
  assert.equal(p.$("#char-c2 .cname").textContent, "Alt");
  assert.equal(p.id("cbChar").textContent, "Alt");
  await p.w.__db.doc("progress/c2-bst").set({ done: { 5: true }, updatedAt: "x" });
  await sleep(20);
  assert.equal(p.countBst(), "1 / 50");
  const before = p.writes().length;
  await p.input("searchInput", "Cu");
  await sleep(FLUSH);
  assert.equal(p.writes().length, before);
});

test("each character keeps its own checks and its own level per list", async () => {
  const p = await load();
  await p.input("levelInput", "20");
  p.id("char-c2").click(); await sleep(10);
  assert.equal(p.count(), "0 / 124");
  assert.equal(p.id("levelInput").value, "", "the level filter is per character and list");
  p.box(1).click(); await sleep(5); await p.confirm();
  assert.equal(p.count(), "1 / 124");
  await sleep(FLUSH);
  assert.deepEqual(plain(p.writes("progress/c2-blu").at(-1).data.done), { 1: true });
  assert.equal(p.writes("progress/c1-blu").length, 0, "the first character is untouched");
  p.id("char-c1").click(); await sleep(10);
  assert.equal(p.count(), "1 / 124");
  assert.equal(p.id("levelInput").value, "20");
});
