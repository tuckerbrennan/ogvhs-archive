#!/usr/bin/env python3
"""Build the OG VHS archive as portable, dependency-free static pages.

Staging: python3 tools/build.py
Production: OGVHS_ENV=production python3 tools/build.py
             (after domain DNS is configured; see README)
"""
import datetime as dt
import html
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
ENV = os.getenv("OGVHS_ENV", CONFIG["environment"])
if ENV not in {"staging", "production"}:
    raise SystemExit("OGVHS_ENV must be staging or production")
SITE_URL = (os.getenv("OGVHS_SITE_URL") or (CONFIG["productionUrl"] if ENV == "production" else CONFIG["siteUrl"])).rstrip("/")
BASE_PATH = os.getenv("OGVHS_BASE_PATH") or ("/" if ENV == "production" else CONFIG["basePath"])
BASE_PATH = "/" + BASE_PATH.strip("/") + ("/" if BASE_PATH.strip("/") else "")
DIST = ROOT / "dist"
VINE_ID_RE = re.compile(r"^[A-Za-z0-9]{11}$")
HASHTAG_RE = re.compile(r"(?<![\w])#([\w]+)", re.UNICODE)


def esc(value):
    return html.escape(str(value), quote=True)


def route(page=""):
    return BASE_PATH + page.strip("/") + ("/" if page.strip("/") else "")


def abs_route(page=""):
    return SITE_URL + route(page)


def safe_url(s):
    if not s:
        return ""
    s = str(s)
    p = urlparse(s)
    if p.scheme in ("https", "http") and p.netloc:
        return s
    return ""


def published_date(value):
    if not value:
        return ("Date unknown", "")
    try:
        d = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (d.strftime("%b %-d, %Y"), d.date().isoformat())
    except (TypeError, ValueError):
        raise ValueError(f"Invalid publishedAt: {value!r}")


def tags_for(caption, explicit):
    out = []
    seen = set()
    for t in ([m.group(1) for m in HASHTAG_RE.finditer(caption or "")] + (explicit or [])):
        t = str(t).strip().lstrip("#").casefold()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def caption_html(caption):
    if not caption:
        return '<span class="muted">Caption not recovered</span>'
    parts, last = [], 0
    for m in HASHTAG_RE.finditer(caption):
        parts.append(esc(caption[last:m.start()]))
        tag = m.group(1).casefold()
        parts.append(f'<a href="{esc(route("tag/" + quote(tag, safe="")))}">{esc(m.group(0))}</a>')
        last = m.end()
    parts.append(esc(caption[last:]))
    return "".join(parts)


def read_catalog():
    raw = json.loads((ROOT / "data/vines.json").read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("data/vines.json must be a JSON array")
    found = set()
    clean = []
    for n, row in enumerate(raw, 1):
        vid = str(row.get("vineId") or "")
        if not VINE_ID_RE.fullmatch(vid):
            raise ValueError(f"Row {n}: vineId must be exactly 11 alphanumeric characters")
        if vid in found:
            raise ValueError(f"Duplicate vineId: {vid}")
        found.add(vid)
        raw_caption = row.get("rawCaption")
        if raw_caption is not None and not isinstance(raw_caption, str):
            raise ValueError(f"Row {n}: rawCaption must be text or null")
        vurl = safe_url(row.get("videoUrl"))
        if row.get("videoUrl") and not vurl:
            raise ValueError(f"Row {n}: videoUrl must be a fully-qualified http(s) URL")
        poster = safe_url(row.get("thumbnailUrl"))
        if row.get("thumbnailUrl") and not poster:
            raise ValueError(f"Row {n}: thumbnailUrl must be a fully-qualified http(s) URL")
        d, date_sort = published_date(row.get("publishedAt"))
        extra = row.get("tags") or []
        if not isinstance(extra, list):
            raise ValueError(f"Row {n}: tags must be a list")
        tags = tags_for(raw_caption, extra)
        clean.append({"vineId": vid, "videoUrl": vurl, "thumbnailUrl": poster, "rawCaption": raw_caption, "publishedAt": date_sort or None, "dateLabel": d, "tags": tags, "sourceFilename": row.get("sourceFilename") or None, "restoredAt": row.get("restoredAt") or None})
    # newest first, unknown dates at the end; then alphabetical ID so builds deterministic
    clean.sort(key=lambda r: (r["publishedAt"] is None, -(int(r["publishedAt"].replace("-", ""))) if r["publishedAt"] else 0, r["vineId"]))
    return clean


def chrome(content, title, active="", description=None, page="", is_home=False):
    title_tag = f"{title} | OG VHS" if title != "OG VHS" else "OG VHS — The Vine Archive"
    # Staging URLs should not be canonical. This avoids search-engine identity drift.
    canonical = f'<link rel="canonical" href="{esc(abs_route(page))}">' if ENV == "production" else '<meta name="robots" content="noindex, nofollow">'
    menu = [("Archive", "archive"), ("Hashtags", "tags"), ("About", "about")]
    nav = "".join(f'<a href="{esc(route(path))}" class="{"active" if active == path else ""}" {"aria-current=page" if active == path else ""}>{esc(label)}</a>' for label, path in menu)
    logo = f'<a class="brand" href="{esc(route())}" aria-label="OG VHS home"><img src="{esc(route("assets/mark.svg"))}" alt=""><strong>OG VHS</strong><span>THE VINE<br>ARCHIVE</span></a>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0c110f"><meta name="description" content="{esc(description or CONFIG['description'])}">{canonical}<title>{esc(title_tag)}</title><link rel="icon" type="image/svg+xml" href="{esc(route("assets/mark.svg"))}"><link rel="stylesheet" href="{esc(route("assets/styles.css"))}"><script defer src="{esc(route("assets/app.js"))}"></script></head><body data-base="{esc(BASE_PATH)}"><header class="top"><div class="wrap top-inner">{logo}<nav class="nav" aria-label="Main navigation">{nav}<a class="nav-index" href="{esc(route("archive"))}">Explore ↗</a></nav></div></header><main id="main-content">{content}</main><footer class="foot"><div class="wrap foot-inner"><div><strong class="brand" style="font-size:22px">OG VHS</strong><p class="mini muted">A home for six-second artifacts. Independent archive.</p></div><nav class="mini muted" aria-label="Footer"><a href="{esc(route())}">Home</a><a href="{esc(route("archive"))}">Archive</a><a href="{esc(route("tags"))}">Tags</a><a href="{esc(route("about"))}">About</a></nav></div></footer></body></html>'''


def heading(page, label, title, lead, crumb="Home / Archive"):
    chunks = crumb.split(" / ")
    c = f'<a href="{esc(route())}">Home</a>'
    if len(chunks) > 1:
        c += f'<span>/</span>{esc(chunks[-1])}'
    return f'<section class="page-head"><div class="wrap"><p class="crumb">{c}</p><p class="mini lime">{esc(label)}</p><h1 class="page-title">{title}</h1><p class="page-lead">{lead}</p></div></section>'


def empty_state(title="The tapes are being cataloged", message="Original videos and captions will appear here as they are recovered. Nothing has been invented to fill the shelves."):
    return f'<div class="empty"><div class="empty-inner"><div class="empty-icon" aria-hidden="true">⌁</div><p class="mini lime">ARCHIVE STATUS / AWAITING TRANSFER</p><h3>{esc(title)}</h3><p>{esc(message)}</p></div></div>'


def thumb(v):
    vid = v["vineId"]
    if v["videoUrl"]:
        poster = f' poster="{esc(v["thumbnailUrl"])}"' if v["thumbnailUrl"] else ""
        content = f'<video muted loop playsinline preload="none"{poster} data-preview-src="{esc(v["videoUrl"])}" aria-label="Preview of Vine {esc(vid)}"></video>'
    elif v["thumbnailUrl"]:
        content = f'<img src="{esc(v["thumbnailUrl"])}" loading="lazy" alt="Thumbnail for Vine {esc(vid)}">'
    else:
        content = '<div class="no-media">OG<span>MEDIA PENDING</span></div>'
    return f'<div class="vine-thumb">{content}<span class="thumb-id">{esc(vid)}</span><span class="thumb-play" aria-hidden="true">▶</span></div>'


def card(v):
    vid=v["vineId"]
    excerpt = (v["rawCaption"] or "Caption not recovered").replace("\n", " ")
    if len(excerpt)>110: excerpt=excerpt[:107]+"…"
    return f'<article class="vine-card"><a href="{esc(route("v/"+vid))}" aria-label="View Vine {esc(vid)}">{thumb(v)}</a><h3><a href="{esc(route("v/"+vid))}">{esc(excerpt)}</a></h3><p class="card-meta"><span>{esc(v["dateLabel"])}</span>{"<span class=status>• Metadata pending</span>" if not v["rawCaption"] or not v["publishedAt"] else ""}</p></article>'


def browser(vines, title="Archive", tag=None):
    label = "FILTER / ARCHIVE" if tag else "THE COLLECTION / ALL TAPES"
    intro = f'Every recovered clip bearing #{esc(tag)}.' if tag else 'Browse the collection. Search captions, hashtags or original Vine IDs.'
    banner = heading("archive", label, f'#{esc(tag)}' if tag else 'THE ARCHIVE.', intro, "Home / Hashtag" if tag else "Home / Archive")
    empty_copy = "No clips are cataloged yet. The archive will populate as original files are imported." if not vines else "No matching Vines. Try another search."
    search = (f'<section class="browser"><div class="wrap"><div class="filters">'
        f'<div class="field"><label class="mini" for="archive-search">Search the tapes</label>'
        f'<div class="searchbox"><input id="archive-search" type="search" autocomplete="off" placeholder="Vine ID, caption, #hashtag…" aria-controls="results"></div></div>'
        f'<div class="selectfield"><label class="mini" for="archive-sort">Sort by</label>'
        f'<select id="archive-sort"><option value="newest">Newest first</option><option value="oldest">Oldest first</option><option value="restored">Recently restored</option></select></div></div>'
        f'<div class="browse-head"><span id="result-count" class="mini">{len(vines)} RECORDS</span><span class="mini">OG VHS / ARCHIVE</span></div>'
        f'<div id="results" class="gallery" aria-live="polite">{"".join(card(v) for v in vines[:24])}</div>'
        f'<div id="empty-results" class="no-results" style="display:{"none" if vines else "block"}">{esc(empty_copy)}</div>'
        f'<button type="button" class="loadmore" id="load-more" style="display:{"block" if len(vines)>24 else "none"}">Load more tapes ↓</button>'
        f'</div></section>')
    # Embed as safe JSON, with the canonical catalog also available at /data/catalog.json.
    safe_data = json.dumps(vines, ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    data = f'<script type="application/json" id="archive-data">{safe_data}</script>'
    tag_marker = f'<div id="archive-mode" data-tag="{esc(tag or "")}" hidden></div>'
    return banner+search+data+tag_marker


def home(vines, tags):
    count=len(vines)
    hero = f'''<section class="herowrap"><div class="wrap hero"><div class="hero-copy"><p class="eyebrow mini"><span class="signal"></span> THE OG VHS ARCHIVAL PROJECT · EST. 2013</p><h1 class="hero-title">THE INTERNET<br><span class="outline">USED TO</span><br><span class="last">LOOP.</span></h1><p class="lead">A permanent home for six-second artifacts. The fleeting, the absurd, and the very good bad ideas we once posted online.</p><a class="pill-link" href="{esc(route('archive'))}">Explore the archive <span aria-hidden="true">↗</span></a></div><div class="hero-art" role="img" aria-label="Illustration of a vintage OG VHS videocassette"><div class="float-stamp">PRESERVING<br>THE INTERNET</div><div class="tape"><div class="tape-head"><small>THE ORIGINAL COLLECTION</small><strong>OG VHS</strong></div><div class="reels"><div class="reel"></div><div class="reel"></div></div><div class="tape-bottom">SIX SECONDS · INFINITE REWINDS</div></div></div></div></section><div class="strip"><div class="wrap strip-inner"><span class="mini">INDEPENDENT DIGITAL PRESERVATION</span><span class="dots" aria-hidden="true">• • •</span><span class="mini">{count} VERIFIED CLIPS CATALOGED</span></div></div>'''
    latest = "".join(card(v) for v in vines[:8]) if vines else empty_state()
    return hero+f'''<section class="section"><div class="wrap"><div class="section-head"><div><p class="mini lime">01 / THE COLLECTION</p><h2 class="section-title">Recently<br>recovered.</h2></div><a class="underline-link" href="{esc(route('archive'))}">SEE ALL TAPES ↗</a></div>{f'<div class="gallery">{latest}</div>' if vines else latest}</div></section><section class="section" style="padding-top:0"><div class="wrap"><div class="section-head"><div><p class="mini lime">02 / WHY IT EXISTS</p><h2 class="section-title">A little piece<br>of the internet.</h2></div></div><div class="feature-row"><div class="feature"><b>01 — KEEP IT</b><h3>Too good to disappear.</h3><p>Platforms vanish. Original files do not have to. This is about keeping the odd little moments intact.</p></div><div class="feature"><b>02 — FIND IT</b><h3>Every clip has an ID.</h3><p>Each recovered Vine retains its original 11-character identifier, independent of where the video is stored.</p></div><div class="feature"><b>03 — REMEMBER IT</b><h3>Original words matter.</h3><p>Captions, dates and hashtags will be restored as evidence is found. Missing information stays missing.</p></div></div></div></section><section class="banner"><div class="wrap banner-in"><div><p class="mini">A NOTE FROM THE ARCHIVE</p><h2>THE FORMAT WAS TEMPORARY.<br>THE MEMORIES AREN'T.</h2><p>A growing independent record of OG VHS and an internet that moved six seconds at a time.</p></div><a href="{esc(route('about'))}">ABOUT THIS PROJECT ↗</a></div></section>'''


def tags_page(tag_counts):
    head = heading("tags", "INDEX / KEYWORDS", "ALL THE TAGS.", "Every recovered hashtag, organized in one place.", "Home / Hashtags")
    if not tag_counts:
        content=empty_state("No hashtags cataloged yet", "When original Vine captions are recovered, their hashtags will appear here automatically.")
    else:
        content='<div class="tags">'+''.join(f'<a class="tag-pill" href="{esc(route("tag/"+quote(t,safe="")))}">#{esc(t)} <span>{c:02}</span></a>' for t,c in sorted(tag_counts.items(),key=lambda p:(-p[1],p[0])))+'</div>'
    return head+f'<section class="section"><div class="wrap">{content}</div></section>'

def detail_page(v):
    vid=v["vineId"]
    if v["videoUrl"]:
        poster=f' poster="{esc(v["thumbnailUrl"])}"' if v['thumbnailUrl'] else ''
        player=f'<video id="vine-player" controls playsinline preload="metadata" src="{esc(v["videoUrl"])}"{poster} aria-label="Vine {esc(vid)}"></video>'
        open_action=f'<a class="smallbutton" href="{esc(v["videoUrl"])}" target="_blank" rel="noopener noreferrer">OPEN VIDEO ↗</a>'
        loop_action='<button class="smallbutton" id="toggle-loop" type="button" aria-pressed="false">LOOP OFF</button>'
    else:
        player='<div class="empty" style="width:100%;height:100%;min-height:unset"><div class="empty-inner"><div class="empty-icon">⌁</div><p class="mini lime">VIDEO NOT YET AVAILABLE</p><h3>Media pending</h3><p>The original video file has not been attached to this record.</p></div></div>'
        open_action=loop_action=''
    taglist=''.join(f'<a class="tag-pill" href="{esc(route("tag/"+quote(t,safe="")))}">#{esc(t)}</a>' for t in v['tags']) if v['tags'] else '<p class="muted">No verified hashtags</p>'
    meta_status = 'CAPTION PENDING' if not v['rawCaption'] else 'CAPTION RECOVERED'
    return f'''<div class="wrap"><div class="record"><div><p class="crumb"><a href="{esc(route('archive'))}">← BACK TO ARCHIVE</a></p><div class="player" style="margin-top:23px">{player}</div></div><aside><div class="record-head"><p class="mini lime">ORIGINAL VINE RECORD</p><h1>{esc(vid)}</h1><span class="mini muted">{esc(v['dateLabel'])}</span></div><div class="record-section"><h2 class="mini">CAPTION / ORIGINAL TEXT</h2><div class="caption">{caption_html(v['rawCaption'])}</div></div><div class="record-section"><h2 class="mini">TAGS / INDEXED</h2><div class="record-tags">{taglist}</div></div><div class="record-section"><h2 class="mini">ARCHIVE INFORMATION</h2><p class="mini muted">VINE ID: {esc(vid)}</p><p class="mini muted">STATUS: {meta_status}</p><p class="mini muted">SOURCE: {esc(v['sourceFilename'] or 'NOT DOCUMENTED')}</p></div><div class="record-actions">{open_action}<button class="smallbutton" id="copy-link" type="button">COPY LINK</button>{loop_action}</div></aside></div></div>'''


def about_page(count):
    return heading("about", "INDEPENDENT ARCHIVE / OUR MISSION", "WHY OG VHS?", "The format was temporary. The memories aren't.", "Home / About")+f'''<section class="section"><div class="wrap"><div class="about-text"><p>For a while, the internet was built around <strong>six seconds at a time</strong>. Tiny loops became jokes, conversations, odd experiments, and little accidental time capsules.</p><p><strong>OG VHS</strong> is an independent project to preserve original Vine posts before they vanish into forgotten hard drives, broken links, and out-of-date platforms.</p><p>The archive currently contains <strong>{count} verified record{'s' if count != 1 else ''}</strong>. The goal is accuracy over completeness: the original Vine ID is kept as the permanent identity for a clip, and captions, hashtags, and dates are included only when they're known.</p><p>No made-up quotes or fabricated posting dates. If we haven't recovered a caption, you'll see <span class="code">Caption not recovered</span>. It's a work in progress, and that's part of its story.</p><p>The public archive is read-only. Source files are held separately from this site, so the collection can move to OGVHS.com or another host without losing its identity.</p></div></div></section>'''


def write(page, contents):
    folder=DIST / page.strip("/")
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"index.html").write_text(contents,encoding="utf-8")


def build():
    vines=read_catalog()
    counts={}
    for v in vines:
        for t in v['tags']:
            counts[t]=counts.get(t,0)+1
    if DIST.exists(): shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(ROOT/"assets",DIST/"assets")
    (DIST/"data").mkdir()
    # Client only receives public archival information, never private source notes.
    (DIST/"data"/"catalog.json").write_text(json.dumps(vines,ensure_ascii=False,separators=(',',':')),encoding="utf-8")
    write("",chrome(home(vines,counts),"OG VHS", active=""))
    write("archive",chrome(browser(vines),"Archive",active="archive",page="archive"))
    write("tags",chrome(tags_page(counts),"Hashtags",active="tags",page="tags"))
    write("about",chrome(about_page(len(vines)),"About",active="about",page="about"))
    for tag in counts:
        clips=[v for v in vines if tag in v['tags']]
        slug=quote(tag,safe="")
        write("tag/"+slug,chrome(browser(clips,tag=tag),f"#{tag}",active="tags",page="tag/"+slug))
    for v in vines:
        write("v/"+v['vineId'],chrome(detail_page(v),f"Vine {v['vineId']}",page="v/"+v['vineId'],description=(v['rawCaption'] or f"Archived Vine {v['vineId']}")))
    missing=heading("404", "NOT FOUND", "TAPE MISSING.", "This record isn't in the archive yet.", "Home / Missing")+f'<section class="section"><div class="wrap"><a class="pill-link" href="{route("archive")}">BACK TO ARCHIVE ↗</a></div></section>'
    (DIST/"404.html").write_text(chrome(missing,"Not Found"),encoding="utf-8")
    (DIST/"robots.txt").write_text("User-agent: *\nDisallow: /\n" if ENV=="staging" else "User-agent: *\nAllow: /\nSitemap: "+SITE_URL+"/sitemap.xml\n")
    if ENV=="production":
        (DIST/"CNAME").write_text(urlparse(SITE_URL).netloc+"\n")
        links=[route(""),route("archive"),route("tags"),route("about")]+[route("tag/"+quote(t,safe="")) for t in counts]+[route("v/"+v['vineId']) for v in vines]
        (DIST/"sitemap.xml").write_text('<?xml version="1.0" encoding="utf-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{esc(SITE_URL+l)}</loc></url>' for l in links)+'</urlset>')
    print(f"Built {len(vines)} Vine records, {len(counts)} tags, {ENV} pages in {DIST}")
    print(f"Base URL: {SITE_URL}{BASE_PATH}")

if __name__ == "__main__":
    build()
