# OG VHS — The Vine Archive

A responsive, independent archive of original OG VHS Vine videos. Zero paid builder or database dependencies.

> **Status:** Staging contains 10 playable user-supplied web copies. Original captions, posting dates, and Vine IDs remain unverified and are not fabricated. Original-resolution sources are kept outside GitHub.

## Local preview and build

Requires Python 3.10+ (no third-party Python or Node packages):

```sh
python3 tools/build.py
python3 -m http.server 8000 --directory dist
```

Note: The staging build uses the GitHub Pages base path `/ogvhs-archive/`. For local testing on `http://localhost:8000/`, use `OGVHS_BASE_PATH=/ python3 tools/build.py` and then open `http://localhost:8000/`. Restore staging settings by running `python3 tools/build.py` before committing if you manually upload `dist` (the docs branch publisher does not rebuild automatically).

## Deploy on GitHub Pages (staging)

The public GitHub repository is `tuckerbrennan/ogvhs-archive`. The `docs/` folder contains a **prebuilt version of the site**, allowing GitHub Pages to publish it directly without requiring GitHub Actions.

1. Open https://github.com/tuckerbrennan/ogvhs-archive/settings/pages
2. Under **Build and deployment**, select **Deploy from a branch** (not GitHub Actions).
3. Choose branch **main** and folder **/docs**, then click **Save**.
4. GitHub will publish the staging site to https://tuckerbrennan.github.io/ogvhs-archive/ after deployment.

To update content, edit `data/vines.json`, then run `python3 tools/build.py` locally and copy the generated `dist/` contents into `docs/`. Commit **both** the content changes and the regenerated `docs/` files. An optional GitHub Actions workflow is included for when workflow runners are available, but is not required. The site is accessible publicly once Pages is enabled, though staging pages request `noindex` in their HTML and `robots.txt`; these are requests to search engines, not privacy guarantees.

## Production switch for OGVHS.com — no DNS changes now

All internal links are built from `config.json`/environment variables. There are no hard-coded GitHub URLs in archive pages or media records. Original Vine IDs determine permanent record paths:

- Staging: `/ogvhs-archive/v/50W0x3Pu6xJ/`
- Future production: `/v/50W0x3Pu6xJ/`

When you are ready to connect `ogvhs.com`, run `OGVHS_ENV=production python3 tools/build.py`, copy the output into `docs/`, and configure the Pages custom domain in GitHub and your DNS provider. Production builds use `https://ogvhs.com`, an empty base path, `CNAME`, canonical links, and a sitemap; staging builds use a prefixed path and noindex tags. **Do not enable the production environment before domain verification and DNS setup.** GitHub Pages custom-domain redirects may be available after the domain is configured, but do not assume that every existing staging URL will permanently redirect; verify links during launch.

If a different hosting provider is chosen, the build can move with no application rewrite.

## Archive data format

`data/vines.json` is the only source of truth. It starts as `[]` and accepts entries such as:

```json
{
  "vineId": "50W0x3Pu6xJ",
  "videoUrl": null,
  "thumbnailUrl": null,
  "rawCaption": null,
  "publishedAt": null,
  "tags": [],
  "sourceFilename": "50W0x3Pu6xJ.mp4"
}
```

This is an **illustrative record shape only**, not a claimed historical post. `videoUrl` must be a publicly playable `https` link to the actual MP4. Do not paste a private Google Drive download URL expecting it to stream reliably. Optional `publishedAt` dates should be accurate ISO timestamps or dates. Captions remain verbatim; tags are extracted from `#hashtags` automatically or merged with explicitly given tags. All public pages are generated per ID.

## Import media filenames without touching the videos

```sh
python3 tools/import_vines.py --folder '/path/to/VineDatesUpdated' --dry-run
python3 tools/import_vines.py --folder '/path/to/VineDatesUpdated'
```

This scans recursively, ignores Mac `._` sidecars, recognizes IDs in `50W0x3Pu6xJ.mp4` or `50W0x3Pu6xJ.sub.mp4`, and writes a verified-ID catalog. Videos are **not uploaded to GitHub**. Records without a playable `videoUrl` have an honest media-pending placeholder.

When a caption export is recovered:

```sh
python3 tools/import_vines.py --metadata '/path/to/archive.csv' --dry-run
python3 tools/import_vines.py --metadata '/path/to/archive.csv'
python3 tools/build.py
```

Supported metadata formats: CSV or an array/wrapped-array JSON, with fields such as `vineId`, `caption`, `createdAt` and `tags`. The importer merges by ID; **blank incoming fields never erase existing captions or dates**. Review the catalog and commit it to GitHub to publish updates. For large archives, we can automate media uploads separately using R2 or another video store. Never publish API keys or account access tokens.

## Tests

```sh
python3 -m unittest discover -s tests -v
python3 tools/build.py
```

## Hosting cost

GitHub Pages is free for public repositories; this site does not require GitHub Actions. Large video files should live on a separate public media host; video storage and playback may have separate usage charges.

## Status / next steps

- [x] Responsive, original retro-designed website
- [x] Search, date sorting, load more and hashtag routes
- [x] Static Vine ID pages and caption hyperlinks
- [x] Portable staging/production configuration
- [x] Filename and metadata import tool
- [x] GitHub Actions Pages deployment workflow
- [x] Create the public GitHub repository `tuckerbrennan/ogvhs-archive`
- [x] Push site files and prebuilt `docs/` directory
- [ ] Select **Deploy from a branch** and **main /docs** in Pages settings
- [ ] Import only verified original OG VHS videos; add metadata as recovered
- [ ] Select and configure actual video host
- [ ] Connect OGVHS.com and verify redirects/SEO once ready

## Initial 10-ID import (2026-10-29)

The first ten entries are **identifier-only records**, selected from AppleDouble `._*.mp4` files in the Google Drive `Lacie/VineDatesUpdated` folder. These sidecar files are **not videos**. Matching `.sub.mp4` files found in Dropbox `VineSubs` were zero bytes and are not used as media. No video bytes, timestamps, captions, or hashtags have been recovered for these ten entries. The website marks each as **MEDIA PENDING**, and the catalog retains provenance in `sourceEvidence`. These are not counted as playable restored clips.

To complete the import, locate and upload the real `ID.mp4` file for each Vine to a public video host, then fill the `videoUrl` on its matching catalog record and rebuild `docs/`.


## First playable media batch: 10 user-uploaded clips (Oct 29, 2026)

The first playable demo batch contains exactly ten user-supplied videos; the original files are preserved outside this GitHub repository. Web-optimized MP4s and JPEG posters live at `docs/media/` and are served without an external media provider. Public staging media is available through the GitHub Pages deployment. The files include one roughly ten-second ABC clip; do not assume every uploaded clip was a six-second Vine post.

Most filenames (e.g. `IMG_2915.mp4`) **are not original Vine identifiers**. To avoid inventing history, each receives a stable 11-character **archive reference** formed from its content hash (prefixed with `m`); the catalog labels these records `idKind: archive` and leaves original Vine ID, posting date, hashtags, and caption pending. When authentic IDs are recovered, add a verified `originalVineId` mapping while preserving published archive reference URLs (add redirects or aliases later).

`data/pending_vines.json` preserves the previous ten sidecar-only metadata references separately; these are intentionally excluded from the playable gallery. `mediaPath` and `posterPath` are site-relative, resolved by `tools/build.py` against the configured environment base path. Nothing links permanently to `tuckerbrennan.github.io`, so the final domain switch remains portable.

To add a video from a local source, create an optimized MP4 and JPEG thumbnail under `docs/media/<archive-ref>.*`, add its record to `data/vines.json`, build with `python3 tools/build.py`, and replace `docs/` with `dist/`. Never put original full-resolution source footage into the public repository.

## Vault presentation settings (October 29, 2026)

The public navigation calls the gallery **The Vault**, keeping the existing `/archive/` URL intact to avoid breaking bookmarks. The overly technical “Every clip has an ID” feature box was removed. Clip pages start with **looping ON** and retain a loop toggle. Desktop hover previews attempt audio playback; browsers that block hover-triggered sound fall back to a muted preview with a visible **ENABLE SOUND** button that can be clicked. Touch/mobile visitors play sound with their usual tap on a video detail page.
