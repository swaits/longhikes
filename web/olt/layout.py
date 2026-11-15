"""The shared page frame: <head>, header and navigation, footer.

To add a page (see also docs in pages.py):

    from olt.layout import layout, page_head, write_page
    from olt.markup import esc

    body = page_head("Places", lede="Trails by state and province.")
    body += f'<div class="container prose">...{esc(some_text)}...</div>'
    html = layout("Places", body, path="/regions/", description="Long trails by place.")
    write_page(out_dir, "/regions/", html)

`path` is the page's own site path; it sets the canonical link (when
site.toml has base_url) and marks the current item in the navigation.
Everything else on the page comes from style.css and app.js; no inline
scripts or styles (the Content-Security-Policy forbids them).
"""
import json
import os

from . import common, site as site_settings
from .markup import Markup, attrs, esc, json_block

NAV = (
    ("Trails", "/"),
    ("Places", "/regions/"),
    ("About", "/about/"),
)
# Pages with no header item of their own, and the item they sit under. The
# lists (Routes among them) are part of Trails; the dataset pages are part of
# About and are linked from the About hub and the footer.
NAV_PARENT = {"/trails/": "/", "/lists/": "/", "/routes/": "/",
              "/sources/": "/about/", "/logos/": "/about/", "/data/": "/about/"}

FONT_PRELOADS = (
    "/assets/fonts/source-serif-4-latin.woff2",
    "/assets/fonts/ibm-plex-sans-condensed-400-latin.woff2",
)
MAPLIBRE_CSS = "/assets/vendor/maplibre-gl/maplibre-gl.css"
MAPLIBRE_JS = "/assets/vendor/maplibre-gl/maplibre-gl.js"
# The outdoor map of the trail pages: its style, named on each trail map figure
# (data-outdoor) for app.js to fetch, and the contour add-on (maplibre-contour),
# loaded on those pages only (layout(outdoor=True)).
OUTDOOR_STYLE = "/assets/map/outdoor.json"
CONTOUR_JS = "/assets/vendor/maplibre-contour/maplibre-contour.js"


def _current(path, href):
    """True when the nav item href is the section the page at path belongs to."""
    if href == "/" and path == "/":
        return True
    if any(path.startswith(p) and parent == href for p, parent in NAV_PARENT.items()):
        return True
    return href != "/" and path.startswith(href)


SAVED_PATH = "/saved/"

THEMES = (("auto", "Auto"), ("light", "Light"), ("dark", "Dark"))


def prefs():
    """The reader's two display choices, at the right of the header on every page.

    Units: a two-way switch, mi or km first (radios named "units", as every
    units switch on the site; app.js keeps them in step and fires olt:units).
    Theme: a small menu built from <details>, its button showing the theme in
    use (its icon, and its name where there is room); the menu holds the three
    themes as radios named "theme" (app.js fires olt:theme). The icon and name
    in the button follow <html data-theme>, which prefs.js sets before first
    paint, so the button is right from the start. Both need JavaScript and are
    hidden without it (.js-only).
    """
    icons = "".join(f'<span class="theme__icon theme__icon--{k}">{common.ICON_THEME[k]}</span>' for k, _ in THEMES)
    now = "".join(f'<span class="theme__now--{k}">{label}</span>' for k, label in THEMES)
    hint = {"auto": '<span class="vh">, </span><small>As your device is set</small>'}
    options = "".join(
        f'<label class="theme__option"><input type="radio" name="theme" value="{k}"{" checked" if k == "auto" else ""}>'
        f'<span class="theme__choice">{common.ICON_THEME[k]}<span class="theme__label">{label}{hint.get(k, "")}'
        f'</span></span></label>'
        for k, label in THEMES)
    return Markup(f"""<div class="prefs js-only">
      <fieldset class="prefs__units">
        <legend class="vh">Units</legend>
        <div class="seg seg--prefs">
          <label><input type="radio" name="units" value="mi" checked><span aria-hidden="true">mi</span><span class="vh">Miles and feet</span></label>
          <label><input type="radio" name="units" value="km"><span aria-hidden="true">km</span><span class="vh">Kilometres and metres</span></label>
        </div>
      </fieldset>
      <details class="theme" data-theme-menu>
        <summary class="theme__button">{icons}<span class="vh">Theme: </span><span class="theme__now">{now}</span></summary>
        <fieldset class="theme__menu">
          <legend class="vh">Theme</legend>
          {options}
        </fieldset>
      </details>
    </div>""")


def header(path, site):
    items = "".join(
        f'<li><a href="{esc(href)}"{attrs(aria_current="page" if path == href else ("true" if _current(path, href) else None))}>'
        f"{esc(text)}</a></li>"
        for text, href in NAV)
    # The visitor's saved trails: app.js fills in the count. Saving needs
    # JavaScript, so without it the link is not offered.
    items += (f'<li class="nav__saved js-only"><a href="{SAVED_PATH}"'
              f'{attrs(aria_current="page" if path == SAVED_PATH else None)}>{common.ICON_STAR}Saved'
              f'<span class="nav__count" data-saved-count hidden></span></a></li>')
    return Markup(f"""<header class="site-header">
  <div class="container site-header__inner">
    <a class="wordmark" href="/"><img class="wordmark__mark" src="/assets/favicon.svg" alt="" width="28" height="28">{esc(site.name)}</a>
    <nav class="site-nav" aria-label="Main"><ul class="nav">{items}</ul></nav>
    {prefs()}
  </div>
</header>""")


def footer(site):
    report = ""
    if site.repo_url:
        report = (f'<li><a href="{esc(site.correction_url())}">Report a problem</a></li>'
                  f'<li><a href="{esc(site.new_trail_url)}">Suggest a trail</a></li>'
                  f'<li><a href="{esc(site.repo_url)}">Fix or add a trail</a></li>')
    return Markup(f"""<footer class="site-footer">
  <div class="container site-footer__grid">
    <div class="site-footer__about">
      <a class="wordmark" href="/"><img class="wordmark__mark" src="/assets/favicon.svg" alt="" width="28" height="28">{esc(site.name)}</a>
      <p>Not for navigation: tracks vary in quality, some trails are unfinished, and some have no GPX here. Check a trail&rsquo;s own maps before you go.</p>
      <p>The trail data is public domain (CC0-1.0). Each track keeps the terms of its source, named on its page. Tracks from OpenStreetMap are &copy;&nbsp;OpenStreetMap contributors, under the ODbL. Logos belong to their holders and are shown only to identify each trail.</p>
    </div>
    <nav aria-labelledby="footer-browse">
      <h2 id="footer-browse">Trails</h2>
      <ul>
        <li><a href="/">Every trail</a></li>
        <li><a href="/regions/">Places</a></li>
        <li><a href="/lists/">Lists</a></li>
        <li><a href="/routes/">Routes</a></li>
        <li class="js-only"><a href="{SAVED_PATH}">Saved trails</a></li>
      </ul>
    </nav>
    <nav aria-labelledby="footer-project">
      <h2 id="footer-project">About</h2>
      <ul>
        <li><a href="/about/">About {esc(site.name)}</a></li>
        <li><a href="/data/">Data and downloads</a></li>
        <li><a href="/sources/">Sources and their terms</a></li>
        <li><a href="/logos/">Logos</a></li>
        {report}
      </ul>
    </nav>
  </div>
  <div class="site-footer__base">
    <div class="container">{common.FOOTER_MAP_CREDIT}</div>
  </div>
</footer>""")


def _ld_json_block(obj):
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return Markup(f'<script type="application/ld+json">{text}</script>')


def layout(title, body, *, path, description="", maps=False, outdoor=False, scripts=(), data=None, site=None,
           jsonld=None, og_type="website", noindex=False):
    """Return a complete HTML document.

    title        the page's own title ("Arizona National Scenic Trail"); the site
                 name is appended. Empty for the home page: "<name>: <tagline>".
    body         the page content (HTML, Markup or str), placed inside <main>.
    path         the page's site path, e.g. "/regions/" (canonical link, nav state).
    description  meta description; defaults to the site tagline.
    maps         True to load MapLibre (pages with a .mapfig[data-map]).
    outdoor      True as well on a page whose map is an outdoor map (a trail
                 page): loads the contour add-on after MapLibre, deferred.
    scripts      extra same-origin script URLs, loaded with defer after app.js.
    data         optional object, embedded as <script type="application/json" id="page-data">.
    site         settings (olt.site.Site); defaults to web/site.toml.
    noindex      True for a page whose content is the visitor's own (/saved/):
                 search engines are asked not to index it, and it has no
                 canonical address (its address carries the list). seo.py
                 leaves it out of the sitemap.
    """
    site = site or site_settings.load()
    full_title = f"{title} · {site.name}" if title else f"{site.name}: {site.tagline}"
    description = description or site.tagline
    canonical = "" if noindex else site.canonical(path)
    head = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(full_title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
    ]
    if noindex:
        head.append('<meta name="robots" content="noindex">')
    if canonical:
        head.append(f'<link rel="canonical" href="{esc(canonical)}">')
    head += [
        f'<meta property="og:title" content="{esc(full_title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:type" content="{esc(og_type)}">',
        f'<meta property="og:site_name" content="{esc(site.name)}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(full_title)}">',
        f'<meta name="twitter:description" content="{esc(description)}">',
    ]
    if canonical:
        head.append(f'<meta property="og:url" content="{esc(canonical)}">')
    if site.base_url:
        # A PNG: link previews (Reddit, Slack, iMessage) do not draw an SVG.
        image = esc(site.canonical("/assets/og.png"))
        head.append(f'<meta property="og:image" content="{image}">')
        head.append('<meta property="og:image:width" content="1200">')
        head.append('<meta property="og:image:height" content="630">')
        head.append(f'<meta name="twitter:image" content="{image}">')
    if jsonld is not None:
        head.append(str(_ld_json_block(jsonld)))
    head += [
        '<meta name="color-scheme" content="light dark">',
        '<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">',
        '<link rel="icon" href="/assets/favicon-32.png" type="image/png" sizes="32x32">',
        '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">',
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
        if outdoor:
            head.append(f'<script src="{CONTOUR_JS}" defer></script>')
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
