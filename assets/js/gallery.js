/*
 * Public, read-only GitHub Gallery sync.
 *
 * The gallery page carries static fallback photos in its HTML so it remains
 * usable without JavaScript. On page load, replace that snapshot with the
 * current files from images/gallery/ on main. New uploads do not require a
 * GitHub Pages rebuild once this script has been deployed.
 *
 * GitHub Contents API is public and supports CORS for anonymous visitors.
 * Never treat a filename from an API response as HTML.
 */
(function () {
  "use strict";

  var endpoint = "https://api.github.com/repos/brandoncorder/brandoncorder.github.io/contents/images/gallery?ref=main";
  var rawFolder = "https://raw.githubusercontent.com/brandoncorder/brandoncorder.github.io/main/images/gallery/";
  var allowedPhoto = /\.(?:jpg|jpeg|png|webp|gif|avif)$/i;

  function photoName(name) {
    return name.replace(allowedPhoto, "");
  }

  function photoCard(file) {
    var name = photoName(file.name);
    var url = rawFolder + encodeURIComponent(file.name);
    var figure = document.createElement("figure");
    figure.className = "gallery-item";

    var link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.setAttribute("aria-label", "Open full image: " + name);

    var img = document.createElement("img");
    img.src = url;
    img.alt = name;
    img.loading = "lazy";
    img.decoding = "async";
    link.appendChild(img);

    var caption = document.createElement("figcaption");
    caption.textContent = name;
    figure.appendChild(link);
    figure.appendChild(caption);
    return figure;
  }

  async function refreshGallery() {
    var grid = document.getElementById("gallery-grid");
    if (!grid) return;

    try {
      var response = await window.fetch(endpoint, {
        headers: { Accept: "application/vnd.github+json" },
        cache: "no-store"
      });
      if (!response.ok) throw new Error("GitHub returned HTTP " + response.status);
      var list = await response.json();
      if (!Array.isArray(list)) throw new Error("Unexpected gallery listing");

      var photos = list.filter(function (file) {
        return file && file.type === "file" &&
          typeof file.name === "string" && allowedPhoto.test(file.name);
      });
      photos.sort(function (a, b) {
        return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
      });

      var fragment = document.createDocumentFragment();
      photos.forEach(function (file) {
        fragment.appendChild(photoCard(file));
      });

      grid.replaceChildren(fragment);
    } catch (error) {
      // Leave the static HTML snapshot visible when the API is unavailable
      // or its public rate limit has been reached.
      if (window.console && typeof window.console.warn === "function") {
        window.console.warn("Gallery sync unavailable:", error);
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", refreshGallery);
  } else {
    refreshGallery();
  }
})();
