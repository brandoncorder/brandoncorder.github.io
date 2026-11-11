#!/usr/bin/env node
/* Dependency-free behavior tests for the browser gallery synchronization. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const script = fs.readFileSync("assets/js/gallery.js", "utf8");

function element(tag) {
  return {
    tag, children: [], attrs: {}, className: "", textContent: "",
    appendChild(child) { this.children.push(child); return child; },
    setAttribute(name, value) { this.attrs[name] = value; }
  };
}

async function render({ items, ok = true } = {}) {
  const grid = element("div");
  const old = element("figure");
  grid.children.push(old);
  grid.replaceChildren = function (fragment) { this.children = fragment.children; };
  const status = element("p");
  const document = {
    readyState: "complete",
    createElement: element,
    createDocumentFragment() { return element("fragment"); },
    getElementById(id) { return id === "gallery-grid" ? grid : id === "gallery-status" ? status : null; }
  };
  const window = {
    console: { warn() {} },
    fetch: async (url, options) => {
      assert.match(url, /api\.github\.com\/repos\/brandoncorder\/brandoncorder\.github\.io\/contents\/images\/gallery\?ref=main/);
      assert.equal(options.cache, "no-store");
      if (!ok) throw new Error("Network unavailable");
      return { ok: true, json: async () => items };
    }
  };
  vm.runInNewContext(script, { document, window });
  for (let i = 0; i < 5; i++) await new Promise(resolve => setImmediate(resolve));
  return { grid, status, old };
}

(async function () {
  const r = await render({items: [
    { type: "file", name: "Triphora trianthophoros.JPG" },
    { type: "file", name: "Buxbaumia aphylla.JPEG" },
    { type: "file", name: "readme.md" },
    { type: "dir", name: "folder.jpg" }
  ]});
  assert.equal(r.grid.children.length, 2, "only image files shown");
  assert.equal(r.grid.children[0].children[1].textContent, "Buxbaumia aphylla");
  assert.equal(r.grid.children[1].children[1].textContent, "Triphora trianthophoros");
  assert.equal(r.grid.children[1].children[0].children[0].alt, "Triphora trianthophoros");
  assert.match(r.grid.children[1].children[0].href, /Triphora%20trianthophoros\.JPG$/);
  assert.equal(r.status.textContent, "2 photographs");

  const s = await render({items: []});
  assert.equal(s.grid.children.length, 0);
  assert.match(s.status.textContent, /No photographs/);

  const offline = await render({ok: false});
  assert.equal(offline.grid.children.length, 1, "retain static fallback");
  assert.equal(offline.grid.children[0], offline.old);
  assert.match(offline.status.textContent, /temporarily unavailable/);
  console.log("PASS: Gallery loads and sorts photos, preserves exact filename captions, and handles API failures.");
})().catch(error => { console.error(error); process.exit(1); });
