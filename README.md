# OG VHS — The Vine Archive

A responsive, independent archive of original OG VHS Vine videos. Zero paid builder or database dependencies.

> **Status:** The site is built but the verified archive is intentionally empty. No original captions, dates, or videos have been fabricated. No videos are stored in GitHub.

## Local preview and build

Requires Python 3.10+ (no third-party Python or Node packages):

```sh
python3 tools/build.py
python3 -m http.server 8000 --directory dist
```

Note: The staging build uses the GitHub Pages base path `/ogvhs-archive/`. For local testing on `http://localhost:8000/`, use `OGVHS_BASE_PATH=/ python3 tools/build.py` and then open `http://localhost:8000/`. Restore staging settings by running `python3 tools/build.py` before committing if you manually upload `dist` (GitHub Actions rebuilds automatically).

## Deploy on GitHub Pages (staging)

The public repository is `tuckerbrennan/ogvhs-archive`. The `docs/` directory holds a prebuilt site so GitHub Pages can publish without GitHub Actions.

1. Go to https://github.com/tuckerbrennan/ogvhs-archive/settings/pages.
2. Under **Build and deployment**, select **Deploy from a branch**.
3. Set branch to **main** and folder to **/docs**, then **Save**.
4. After GitHub Pages publishes, open https://tuckerbrennan.github.io/ogvhs-archive/.

To update the archive, edit `data/vines.json`, run `python3 tools/build.py`, copy generated `dist/` files into `docs/`, and commit both. The included GitHub Actions workflow is optional and currently not needed.

Staging is publicly accessible but has `noindex` and `robots.txt` instructions; these are not access controls.

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

GitHub Pages and standard public-repository GitHub Actions have free tiers. Large video files should live on a separate public media host; video storage and playback may have separate usage charges.

## Status / next steps

- [x] Responsive, original retro-designed website
- [x] Search, date sorting, load more and hashtag routes
- [x] Static Vine ID pages and caption hyperlinks
- [x] Portable staging/production configuration
- [x] Filename and metadata import tool
- [x] GitHub Actions Pages deployment workflow
- [x] Create the GitHub repository
- [x] Push source and prebuilt site files
- [ ] Set GitHub Pages to **Deploy from a branch** using **main /docs**
- [ ] Import only verified original OG VHS videos; add metadata as recovered
- [ ] Select and configure actual video host
- [ ] Connect OGVHS.com and verify redirects/SEO once ready


## Initial 10-ID index (October 29, 2026)

The first ten entries are **identifier-only** records derived from AppleDouble `._*.mp4` filenames observed in the Google Drive `Lacie/VineDatesUpdated` folder. AppleDouble sidecars are **not playable videos**. Dropbox `VineSubs` had matching `.sub.mp4` filenames but they were zero-byte files. Therefore NO video files, captions, posting dates, or hashtags were restored for these entries. The site labels them MEDIA PENDING. Video files must be recovered and hosted separately before playback works.
