/*
 * Dependency-free behavior checks for the actual theme.js script.
 * Run with: node scripts/test_theme.js
 *
 * Simulates a minimal DOM and both desktop/mobile toggle buttons; verifies
 * system appearance, OS changes, manual preference, and "System" reset.
 */
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const code = fs.readFileSync("assets/js/theme.js", "utf8");
const KEY = "brandon-corder-color-theme";

function mockButton() {
  const attrs = Object.create(null);
  const listeners = Object.create(null);
  const children = {
    ".theme-toggle-label": { textContent: "" },
    ".theme-toggle-symbol": { textContent: "" }
  };
  return {
    attrs,
    children,
    classList: { toggle(name, on) { attrs["class:" + name] = on; } },
    setAttribute(name, value) { attrs[name] = value; },
    querySelector(selector) { return children[selector] || null; },
    addEventListener(name, callback) { listeners[name] = callback; },
    click() {
      assert.ok(listeners.click, "button has a click listener");
      listeners.click({ preventDefault() {} });
    }
  };
}

function site(options = {}) {
  const values = new Map();
  if (options.saved) values.set(KEY, options.saved);

  const events = Object.create(null);
  const root = {
    attrs: Object.create(null),
    style: {},
    setAttribute(name, value) { this.attrs[name] = value; },
    getAttribute(name) { return this.attrs[name] ?? null; }
  };
  const toggles = [mockButton(), mockButton()];
  const resetButtons = [mockButton()];
  const system = {
    matches: Boolean(options.systemDark),
    addEventListener(name, callback) { events["system:" + name] = callback; }
  };

  const document = {
    documentElement: root,
    querySelectorAll(selector) {
      if (selector === "[data-theme-toggle]") return toggles;
      if (selector === "[data-theme-system]") return resetButtons;
      throw new Error("Unexpected DOM query " + selector);
    },
    addEventListener(name, callback) { events["document:" + name] = callback; }
  };
  const window = {
    localStorage: {
      getItem(key) { return values.has(key) ? values.get(key) : null; },
      setItem(key, value) { values.set(key, value); },
      removeItem(key) { values.delete(key); }
    },
    matchMedia(query) {
      assert.equal(query, "(prefers-color-scheme: dark)");
      return system;
    },
    addEventListener(name, callback) { events["window:" + name] = callback; }
  };
  vm.runInNewContext(code, { window, document });
  assert.equal(typeof events["document:DOMContentLoaded"], "function");
  events["document:DOMContentLoaded"]();

  return {
    root, toggles, resetButtons, values, system,
    osChangesTo(dark) {
      system.matches = dark;
      events["system:change"]();
    },
    storageChanged() { events["window:storage"]({key: KEY}); }
  };
}

let t = site({ systemDark: true });
assert.equal(t.root.attrs["data-theme"], "dark", "dark OS gives dark page");
assert.equal(t.root.attrs["data-theme-source"], "system");
assert.equal(t.root.style.colorScheme, "dark");
assert.equal(t.resetButtons[0].attrs["aria-pressed"], "true");

t.osChangesTo(false);
assert.equal(t.root.attrs["data-theme"], "light", "OS changes while in system mode");
t.toggles[0].click();
assert.equal(t.root.attrs["data-theme"], "dark", "desktop manual toggle works");
assert.equal(t.values.get(KEY), "dark");
assert.equal(t.resetButtons[0].attrs["aria-pressed"], "false");
assert.equal(t.toggles[1].attrs["aria-label"], "Switch to light mode", "mobile label syncs");

t.osChangesTo(true);
t.osChangesTo(false);
assert.equal(t.root.attrs["data-theme"], "dark", "OS doesn't override user choice");
t.resetButtons[0].click();
assert.equal(t.values.has(KEY), false);
assert.equal(t.root.attrs["data-theme"], "light");
assert.equal(t.root.attrs["data-theme-source"], "system");

t.osChangesTo(true);
assert.equal(t.root.attrs["data-theme"], "dark", "system changes resume after reset");
t = site({ systemDark: true, saved: "light" });
assert.equal(t.root.attrs["data-theme"], "light", "saved explicit choice respected");
t.toggles[1].click();
assert.equal(t.root.attrs["data-theme"], "dark", "mobile manual toggle works");

t.values.delete(KEY);
t.storageChanged();
assert.equal(t.root.attrs["data-theme-source"], "system", "storage event returns to system");
assert.equal(site({ systemDark: false }).root.attrs["data-theme"], "light", "light OS gives light page");

console.log("PASS: system light/dark, OS changes, desktop/mobile toggles, storage, and reset.");
