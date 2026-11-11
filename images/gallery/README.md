# Gallery photo uploads

Upload photographs **directly into this folder** (`images/gallery/`) on GitHub's **main** branch.

The live Gallery reads the public file list from GitHub when a visitor opens the page. **After the Gallery's updated JavaScript has published once**, future uploads appear automatically, without editing `gallery.html` or waiting for GitHub Pages to rebuild. If the GitHub API is temporarily unavailable, the page displays its last saved photo selection.

## Caption from filename

The caption is precisely the filename without the extension. For example:

- `Triphora trianthophoros.jpg` → **Triphora trianthophoros**
- `Mount Washington 2023.webp` → **Mount Washington 2023**
- `My Orchid Photo.JPG` → **My Orchid Photo**

Image files are sorted alphabetically, and visitors can open each original at full size.

Supported extensions (case-insensitive): JPG, JPEG, PNG, WebP, GIF, and AVIF. Other files, including README.md, are ignored.

Please remove sensitive EXIF metadata (including GPS coordinates) before upload. GitHub stores earlier commits in its history even if you delete and replace a file. Consider keeping photographs web-sized to improve mobile loading.

## Upload steps

Open this folder on GitHub, select **Add file → Upload files**, select your photographs, and commit to `main`. Refresh the Gallery to see the current list.
