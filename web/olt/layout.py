"""The shared page frame: <head>, header and navigation, footer.

To add a page (see also docs in pages.py):

    from olt.layout import layout, page_head, write_page
    from olt.markup import esc

    body = page_head("Regions", kicker="Browse", lede="Trails by state, province and territory.")
    body += f'<div class="container prose">...{esc(some_text)}...</div>'
    html = layout("Regions", body, path="/regions/", description="Long trails by region.")
    write_page(out_dir, "/regions/", html)

`path` is the page's own site path; it sets the canonical link (when
site.toml has base_url) and marks the current item in the navigation.
Everything else on the page comes from style.css and app.js; no inline
scripts or styles (the Content-Security-Policy forbids them).
"""
import json
import os

from . import site as site_settings
from .markup import Markup, attrs, esc, json_block

NAV = (
    ("Trails", "/"),
    ("Regions", "/regions/"),
    ("Routes", "/routes/"),
    ("Sources", "/sources/"),
    ("Logos", "/logos/"),
    ("About", "/about/"),
    ("Data", "/data/"),
)

FONT_PRELOADS = (
    "/assets/fonts/source-serif-4-latin.woff2",
    "/assets/fonts/ibm-plex-sans-condensed-400-latin.woff2",
)
MAPLIBRE_CSS = "/assets/vendor/maplibre-gl/maplibre-gl.css"
MAPLIBRE_JS = "/assets/vendor/maplibre-gl/maplibre-gl.js"


def _current(path, href):
    """True when the nav item href is the section the page at path belongs to."""
    if href == "/":
        return path == "/" or path.startswith("/trails/")
    return path.startswith(href)


def header(path, site):
    items = "".join(
        f'<li><a href="{esc(href)}"{attrs(aria_current="page" if path == href else ("true" if _current(path, href) else None))}>'
        f"{esc(text)}</a></li>"
        for text, href in NAV)
    return Markup(f"""<header class="site-header">
  <div class="container site-header__inner">
    <a class="wordmark" href="/"><span class="wordmark__blaze" aria-hidden="true"></span>{esc(site.name)}</a>
    <nav aria-label="Main"><ul class="nav">{items}</ul></nav>
  </div>
</header>""")


def footer(site):
    report = (f'<li><a href="{esc(site.issues_url)}">Report an error in a record</a></li>'
              if site.issues_url else "")
    return Markup(f"""<footer class="site-footer">
  <div class="container site-footer__grid">
    <div class="site-footer__about">
      <a class="wordmark" href="/"><span class="wordmark__blaze" aria-hidden="true"></span>{esc(site.name)}</a>
      <p>A dataset, not a navigation product: lines vary in quality, some trails are unfinished, and some records have no line at all. Check a trail&rsquo;s own record before using its line.</p>
      <p>The records are public domain (CC0-1.0). Each line keeps the terms of its source, named on its page. Lines from OpenStreetMap are &copy;&nbsp;OpenStreetMap contributors, under the ODbL. Logos belong to their holders and are shown only to identify each trail.</p>
    </div>
    <nav aria-labelledby="footer-data">
      <h2 id="footer-data">Data</h2>
      <ul>
        <li><a href="/data/">About the data and downloads</a></li>
        <li><a href="/data/trails.csv">trails.csv</a>: one row per trail</li>
        <li><a href="/data/index.geojson">index.geojson</a>: every line, simplified</li>
        <li><a href="/sources/">Sources and their terms</a></li>
      </ul>
    </nav>
    <nav aria-labelledby="footer-project">
      <h2 id="footer-project">Project</h2>
      <ul>
        <li><a href="/about/">About {esc(site.name)}</a></li>
        <li><a href="/logos/">Logos and removal requests</a></li>
        {report}
      </ul>
    </nav>
    <div class="site-footer__prefs">
      <fieldset class="field">
        <legend>Theme</legend>
        <div class="seg">
          <label><input type="radio" name="theme" value="auto" checked><span>Auto</span></label>
          <label><input type="radio" name="theme" value="light"><span>Light</span></label>
          <label><input type="radio" name="theme" value="dark"><span>Dark</span></label>
        </div>
      </fieldset>
      <fieldset class="field">
        <legend>Lengths</legend>
        <div class="seg">
          <label><input type="radio" name="units" value="km" checked><span>km first</span></label>
          <label><input type="radio" name="units" value="mi"><span>miles first</span></label>
        </div>
      </fieldset>
    </div>
  </div>
  <div class="site-footer__base">
    <div class="container">Base maps: OpenFreeMap, &copy;&nbsp;OpenMapTiles, data &copy;&nbsp;OpenStreetMap contributors.</div>
  </div>
</footer>""")


def _ld_json_block(obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return Markup(f'<script type="application/ld+json">{text}</script>')


def layout(title, body, *, path, description="", maps=False, scripts=(), data=None, site=None, jsonld=None, og_type="website"):
    """Return a complete HTML document.

    title        the page's own title ("Arizona National Scenic Trail"); the site
                 name is appended. Empty for the home page: "<name>: <tagline>".
    body         the page content (HTML, Markup or str), placed inside <main>.
    path         the page's site path, e.g. "/regions/" (canonical link, nav state).
    description  meta description; defaults to the site tagline.
    maps         True to load MapLibre (pages with a .mapfig[data-map]).
    scripts      extra same-origin script URLs, loaded with defer after app.js.
    data         optional object, embedded as <script type="application/json" id="page-data">.
    site         settings (olt.site.Site); defaults to web/site.toml.
    """
    site = site or site_settings.load()
    full_title = f"{title} · {site.name}" if title else f"{site.name}: {site.tagline}"
    description = description or site.tagline
    canonical = site.canonical(path)
    head = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(full_title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
    ]
    if canonical:
        head.append(f'<link rel="canonical" href="{esc(canonical)}">')
    head += [
        f'<meta property="og:title" content="{esc(full_title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:type" content="{esc(og_type)}">',
        f'<meta property="og:site_name" content="{esc(site.name)}">',
        '<meta name="twitter:card" content="summary">',
        f'<meta name="twitter:title" content="{esc(full_title)}">',
        f'<meta name="twitter:description" content="{esc(description)}">',
    ]
    if canonical:
        head.append(f'<meta property="og:url" content="{esc(canonical)}">')
        head.append(f'<meta property="og:image" content="{esc(site.canonical("/assets/favicon.svg"))}">')
        head.append(f'<meta name="twitter:image" content="{esc(site.canonical("/assets/favicon.svg"))}">')
    if jsonld is not None:
        head.append(str(_ld_json_block(jsonld)))
    head += [
        '<meta name="color-scheme" content="light dark">',
        '<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">',
    ]
    head += [f'<link rel="preload" href="{f}" as="font" type="font/woff2" crossorigin>' for f in FONT_PRELOADS]
    if maps:
        head.append(f'<link rel="stylesheet" href="{MAPLIBRE_CSS}">')
    head += [
        '<link rel="stylesheet" href="/assets/style.css">',
        # Sets the theme and unit preference before first paint (no inline scripts allowed).
        '<script src="/assets/prefs.js"></script>',
    ]
    # app.js first: deferred scripts run in order, and the finder and the rest of the
    # page must not wait for MapLibre (app.js starts the maps when MapLibre arrives).
    head.append('<script src="/assets/app.js" defer></script>')
    if maps:
        head.append(f'<script src="{MAPLIBRE_JS}" defer></script>')
    head += [f'<script src="{esc(s)}" defer></script>' for s in scripts]
    data_block = json_block(data, "page-data") if data is not None else ""
    return f"""<!doctype html>
<html lang="en">
<head>
{chr(10).join(head)}
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
{header(path, site)}
<main id="main">
{body}
</main>
{footer(site)}
{data_block}
</body>
</html>
"""


def page_head(title, *, kicker="", lede="", crumbs=()):
    """A plain page heading block: breadcrumb, kicker, <h1>, lede. For simple pages.

    crumbs is a sequence of (text, href) pairs leading to this page.
    """
    crumb_html = ""
    if crumbs:
        items = "".join(f'<li><a href="{esc(h)}">{esc(t)}</a></li>' for t, h in crumbs)
        crumb_html = (f'<nav class="breadcrumb" aria-label="Breadcrumb"><ol>{items}'
                      f'<li aria-current="page">{esc(title)}</li></ol></nav>')
    kicker_html = f'<p class="kicker">{esc(kicker)}</p>' if kicker else ""
    lede_html = f'<p class="page-head__lede">{esc(lede)}</p>' if lede else ""
    return Markup(f"""<div class="page-head">
  <div class="container">
    {crumb_html}
    <header class="titleblock">
      <div class="titleblock__text">{kicker_html}<h1>{esc(title)}</h1>{lede_html}</div>
    </header>
  </div>
</div>""")


def write_page(out_dir, path, document):
    """Write a page for a site path: "/" -> index.html, "/a/b/" -> a/b/index.html, "/404.html" -> 404.html."""
    rel = path.lstrip("/")
    if not rel or rel.endswith("/"):
        rel += "index.html"
    dest = os.path.join(out_dir, *rel.split("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(document)
    return dest
