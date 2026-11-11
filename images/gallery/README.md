# Gallery photo uploads

Upload photographs **directly into this folder** (`images/gallery/`) on GitHub.

When the upload is committed to `main`, GitHub Pages rebuilds the site and the [Gallery](https://brandoncorder.github.io/gallery.html) automatically includes the image. **You do not need to edit `gallery.html` or add an entry manually.**

## File names become captions

The Gallery uses the filename *without its extension* as the caption, preserving spelling, spaces, punctuation, and capitalization.

Examples:
- `Triphora trianthophoros.jpg` → **Triphora trianthophoros**
- `Mount Washington 2023.webp` → **Mount Washington 2023**
- `My Orchid Photo.JPG` → **My Orchid Photo**

Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.avif` (case-insensitive). Prefer JPG or WebP for photos, and keep files reasonably small for mobile visitors.

Avoid filenames containing `#`, `?`, `%`, or `/`, as those can interfere with URLs. Avoid uploading images with sensitive GPS/location metadata.

Images are displayed alphabetically by filename. Removing a file from this folder also removes it from the Gallery on the next site build.

The original photographs elsewhere under `images/` remain in the separate *Selected Fieldwork Photographs* section.
