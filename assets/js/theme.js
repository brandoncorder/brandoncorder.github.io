/*
 * Website color scheme: system preference by default; optional manual override.
 *
 * An existing explicit choice ("light" or "dark") is retained. Visitors can
 * restore system mode using the "Use system" button. The active theme is
 * applied in <head> before the page paints, and any system preference changes
 * are observed while the site is in system mode.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "brandon-corder-color-theme";
  var savedChoice = null; // null means follow the system appearance.
  var systemQuery = null;

  try {
    if (typeof window.matchMedia === "function") {
      systemQuery = window.matchMedia("(prefers-color-scheme: dark)");
    }
  } catch (error) {
    systemQuery = null;
  }

  function readChoice() {
    try {
      var value = window.localStorage.getItem(STORAGE_KEY);
      return value === "dark" || value === "light" ? value : null;
    } catch (error) {
      return null;
    }
  }

  function systemTheme() {
    return systemQuery && systemQuery.matches ? "dark" : "light";
  }

  function renderControls() {
    var root = document.documentElement;
    var dark = root.getAttribute("data-theme") === "dark";
    var followingSystem = savedChoice === null;
    var toggles = document.querySelectorAll("[data-theme-toggle]");

    for (var i = 0; i < toggles.length; i += 1) {
      var toggle = toggles[i];
      var nextAction = dark ? "Switch to light mode" : "Switch to dark mode";
      toggle.setAttribute("aria-label", nextAction);
      toggle.setAttribute("title", nextAction);
      toggle.setAttribute("aria-pressed", dark ? "true" : "false");

      var label = toggle.querySelector(".theme-toggle-label");
      if (label) label.textContent = dark ? "Light mode" : "Dark mode";

      var symbol = toggle.querySelector(".theme-toggle-symbol");
      if (symbol) symbol.textContent = dark ? "☀" : "☾";
    }

    var resetButtons = document.querySelectorAll("[data-theme-system]");
    for (var j = 0; j < resetButtons.length; j += 1) {
      resetButtons[j].setAttribute("aria-pressed", followingSystem ? "true" : "false");
      resetButtons[j].classList.toggle("is-selected", followingSystem);
      resetButtons[j].setAttribute(
        "title",
        followingSystem ? "Following your device appearance" : "Follow your device appearance"
      );
    }
  }

  function applyChoice() {
    var root = document.documentElement;
    var next = savedChoice || systemTheme();
    root.setAttribute("data-theme", next);
    root.setAttribute("data-theme-source", savedChoice ? "manual" : "system");
    root.style.colorScheme = next;
    renderControls();
  }

  function chooseExplicit(theme) {
    savedChoice = theme === "dark" ? "dark" : "light";
    try {
      window.localStorage.setItem(STORAGE_KEY, savedChoice);
    } catch (error) {
      // The current-page toggle still works without storage permissions.
    }
    applyChoice();
  }

  function restoreSystem() {
    savedChoice = null;
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      // The system preference still applies during this page visit.
    }
    applyChoice();
  }

  // Initialize before layout to avoid a light-to-dark flash.
  savedChoice = readChoice();
  applyChoice();

  // Respond to OS-level switches only while no manual override is selected.
  if (systemQuery) {
    var systemChanged = function () {
      if (savedChoice === null) applyChoice();
    };
    if (typeof systemQuery.addEventListener === "function") {
      systemQuery.addEventListener("change", systemChanged);
    } else if (typeof systemQuery.addListener === "function") {
      systemQuery.addListener(systemChanged);
    }
  }

  window.addEventListener("storage", function (event) {
    if (event.key === STORAGE_KEY || event.key === null) {
      savedChoice = readChoice();
      applyChoice();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    var toggles = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < toggles.length; i += 1) {
      toggles[i].addEventListener("click", function (event) {
        event.preventDefault();
        var current = document.documentElement.getAttribute("data-theme");
        chooseExplicit(current === "dark" ? "light" : "dark");
      });
    }

    var resetButtons = document.querySelectorAll("[data-theme-system]");
    for (var j = 0; j < resetButtons.length; j += 1) {
      resetButtons[j].addEventListener("click", function (event) {
        event.preventDefault();
        restoreSystem();
      });
    }
    renderControls();
  });
})();
