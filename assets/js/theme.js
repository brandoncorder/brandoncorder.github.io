/*
 * Light / dark theme control for the static academic website.
 *
 * - Default stays light, matching the current site.
 * - The visitor can explicitly toggle the theme.
 * - The chosen theme persists across pages when localStorage is available.
 * - Load synchronously in <head> to avoid a flash of the wrong theme.
 * - Progressive enhancement: the rest of the site works without JavaScript.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "brandon-corder-color-theme";

  function readSavedTheme() {
    try {
      var stored = window.localStorage.getItem(STORAGE_KEY);
      return stored === "dark" ? "dark" : "light";
    } catch (error) {
      return "light";
    }
  }

  function setTheme(theme, remember) {
    var next = theme === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", next);
    if (remember) {
      try {
        window.localStorage.setItem(STORAGE_KEY, next);
      } catch (error) {
        // Browser storage can be blocked; the on-page choice still works.
      }
    }
    return next;
  }

  function renderButtons() {
    var dark = document.documentElement.getAttribute("data-theme") === "dark";
    var buttons = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < buttons.length; i += 1) {
      var button = buttons[i];
      button.setAttribute("aria-pressed", dark ? "true" : "false");
      button.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
      button.setAttribute("title", dark ? "Switch to light mode" : "Switch to dark mode");
      var label = button.querySelector(".theme-toggle-label");
      if (label) {
        label.textContent = dark ? "Light mode" : "Dark mode";
      }
      var symbol = button.querySelector(".theme-toggle-symbol");
      if (symbol) {
        symbol.textContent = dark ? "☀" : "☾";
      }
    }
  }

  setTheme(readSavedTheme(), false);

  document.addEventListener("DOMContentLoaded", function () {
    var buttons = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < buttons.length; i += 1) {
      buttons[i].addEventListener("click", function () {
        var current = document.documentElement.getAttribute("data-theme");
        setTheme(current === "dark" ? "light" : "dark", true);
        renderButtons();
      });
    }
    renderButtons();
  });
})();
