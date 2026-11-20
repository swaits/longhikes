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

from . import common, fingerprint, seo, site as site_settings
from .markup import Markup, attrs, esc, json_block

NAV = (
    ("Trails", "/"),
    ("Places", "/regions/"),
    ("Lists", "/lists/"),
    ("About", "/about/"),
)
# Pages with no header item of their own, and the item they sit under. A trail's page is part of
# Trails; the dataset pages are part of About and are linked from the About hub and the footer.
NAV_PARENT = {"/trails/": "/",
              "/parks/": "/regions/", "/ranges/": "/regions/", "/wilderness/": "/regions/",
              "/sources/": "/about/", "/logos/": "/about/", "/data/": "/about/",
              "/left-out/": "/about/", "/method/": "/about/", "/glossary/": "/about/"}
# Under Lists: the lists (Routes among them), the tables and rankings, the authors and the views of
# what is new. A table that collections.toml names has an address of its own; olt/pages.py adds it
# to UNDER_LISTS as it writes the page.
LISTS_PREFIXES = ("/lists/", "/routes/", "/numbers/", "/authors/", "/recent/", "/connected/")
UNDER_LISTS = set()

FEED_PATH = "/feed.xml"  # the Atom feed of the changelog (olt/feed.py)

# The fonts every page draws above the fold: the body face and the three weights of the
# condensed sans (labels, tiles, headings). A weight that arrives after the first paint swaps
# in with different letter widths, and the page shifts as the lines re-wrap (the home page's
# row of lists moved by 0.15 before the 500 and 600 were here).
FONT_PRELOADS = (
    "/assets/fonts/source-serif-4-latin.woff2",
    "/assets/fonts/ibm-plex-sans-condensed-400-latin.woff2",
    "/assets/fonts/ibm-plex-sans-condensed-500-latin.woff2",
    "/assets/fonts/ibm-plex-sans-condensed-600-latin.woff2",
)
CONTOURS = "/assets/contours.svg"
MAPLIBRE_CSS = "/assets/vendor/maplibre-gl/maplibre-gl.css"
MAPLIBRE_JS = "/assets/vendor/maplibre-gl/maplibre-gl.js"
# The outdoor map of the trail pages: its style, named on each trail map figure
# (data-outdoor) for app.js to fetch, and the contour add-on (maplibre-contour),
# loaded with MapLibre on those pages only (layout(outdoor=True)).
OUTDOOR_STYLE = "/assets/map/outdoor.json"
CONTOUR_JS = "/assets/vendor/maplibre-contour/maplibre-contour.js"


def _current(path, href):
    """True when the nav item href is the section the page at path belongs to."""
    if href == "/lists/":
        return path.startswith(LISTS_PREFIXES) or path in UNDER_LISTS
    if any(path.startswith(p) and parent == href for p, parent in NAV_PARENT.items()):
        return True
    return path == "/" if href == "/" else path.startswith(href)


SAVED_PATH = "/saved/"

THEMES = (("auto", "Auto"), ("light", "Light"), ("dark", "Dark"))


def prefs():
    """The reader's two display choices, at the right of the header on every page.

    Units: a two-way switch, mi or km first (radios named "units", the only
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
        <li><a href="/authors/">Route authors</a></li>
        <li class="js-only"><a href="{SAVED_PATH}">Saved trails</a></li>
      </ul>
    </nav>
    <nav aria-labelledby="footer-project">
      <h2 id="footer-project">About</h2>
      <ul>
        <li><a href="/about/">About {esc(site.name)}</a></li>
        <li><a href="/method/">Method: how figures are made</a></li>
        <li><a href="/glossary/">Glossary</a></li>
        <li><a href="/data/">Data and downloads</a></li>
        <li><a href="/sources/">Sources and their terms</a></li>
        <li><a href="/logos/">Logos</a></li>
        <li><a href="/left-out/">Considered and left out</a></li>
        <li><a href="/about/#how-trails-are-chosen">How trails are chosen</a></li>
        <li><a href="/data/changelog/">Changelog</a></li>
        {report}
      </ul>
    </nav>
  </div>
  <div class="site-footer__base">
    <div class="container">{common.FOOTER_MAP_CREDIT}</div>
  </div>
</footer>""")


def _ld_json_block(obj):
    """One JSON-LD script. "<", ">" and "&" are written as \\u escapes, so no text from a
    record can close the script element or start a tag inside it."""
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return Markup(f'<script type="application/ld+json">{text}</script>')


def structured_data(jsonld, body, path, site, noindex=False):
    """The page's JSON-LD as one <script>, or "": the page's own nodes (one dict or a list of
    them, from olt.seo) and a BreadcrumbList equal to the breadcrumb the body shows. A page
    that is not indexed carries none."""
    if noindex:
        return ""
    nodes = list(jsonld) if isinstance(jsonld, (list, tuple)) else ([jsonld] if jsonld else [])
    crumb = seo.breadcrumb_node(body, site, path, seo.breadcrumb_id(site, path))
    if crumb:
        nodes.append(crumb)
    if not nodes:
        return ""
    obj = {"@context": "https://schema.org", **nodes[0]} if len(nodes) == 1 else \
        {"@context": "https://schema.org", "@graph": nodes}
    return str(_ld_json_block(obj))


def skip_links(body):
    """More skip links, for a page with a map before a long list of rows: past the map to the
    filters and the list, and on to the rows themselves. Each shows only while it has keyboard focus
    (style.css .skip-link) and is left out of a page without its target."""
    body = str(body)
    out = ""
    if 'id="browse-list"' in body and 'class="browse__map"' in body:
        out += '<a class="skip-link" href="#browse-list">Skip the map</a>'
    if 'id="entries"' in body:
        out += '<a class="skip-link" href="#entries">Skip to the list of trails</a>'
    return out


def layout(title, body, *, path, description="", maps=False, outdoor=False, scripts=(), data=None, site=None,
           jsonld=None, og_type="website", noindex=False, image="", image_alt="", alternates=()):
    """Return a complete HTML document.

    title        the page's own title ("Arizona National Scenic Trail"). The <title>
                 appends " · <site name>" only when the whole is 60 characters or
                 fewer; the share titles (og:title, twitter:title) never carry it. Empty for the home page: site.toml's
                 home_title, or "<name>: <tagline>" where that is not set.
    body         the page content (HTML, Markup or str), placed inside <main>.
    path         the page's site path, e.g. "/regions/" (canonical link, nav state).
    description  meta description (155 characters); defaults to the site tagline. The share
                 descriptions (og:description, twitter:description) are cut from it to 125.
    maps         True on a page with a .mapfig[data-map]: app.js is given the addresses of
                 MapLibre, and loads it a moment after the page has loaded.
    outdoor      True as well on a page whose map is an outdoor map (a trail
                 page): app.js loads the contour add-on with MapLibre.
    scripts      extra same-origin script URLs, loaded with defer after app.js.
    data         optional object, embedded as <script type="application/json" id="page-data">.
    site         settings (olt.site.Site); defaults to web/site.toml.
    jsonld       the page's own schema.org nodes, one dict or a list (olt.seo builds them
                 from the records). A BreadcrumbList for the breadcrumb in the body is added.
    image        site path of the page's social card (1200 x 630 PNG); the site card
                 /assets/og.png when empty. image_alt describes it.
    alternates   (href, media type, title) of other forms of this page, as <link rel="alternate">.
    noindex      True for a page whose content is the visitor's own (/saved/), or the 404 page:
                 search engines are asked not to index it, and it has no
                 canonical address (its address carries the list). seo.py
                 leaves it out of the sitemap.
    """
    site = site or site_settings.load()
    # The site sets no tables: one written in Markdown or by hand is set as rows (olt/pagekit.py).
    if "<table" in str(body):
        from . import pagekit
        body = Markup(pagekit.untable(body))
    title = title or site.home_title
    tag = common.title_tag(title, site) if title else f"{site.name}: {site.tagline}"
    share_title = title or tag
    description = description or site.tagline
    share_text = common.share_description(description)
    canonical = "" if noindex else site.canonical(path)
    head = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(tag)}</title>",
        f'<meta name="description" content="{esc(description)}">',
    ]
    if noindex:
        head.append('<meta name="robots" content="noindex">')
    if canonical:
        head.append(f'<link rel="canonical" href="{esc(canonical)}">')
    head += [
        f'<meta property="og:title" content="{esc(share_title)}">',
        f'<meta property="og:description" content="{esc(share_text)}">',
        f'<meta property="og:type" content="{esc(og_type)}">',
        f'<meta property="og:site_name" content="{esc(site.name)}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(share_title)}">',
        f'<meta name="twitter:description" content="{esc(share_text)}">',
    ]
    if canonical:
        head.append(f'<meta property="og:url" content="{esc(canonical)}">')
    if site.base_url:
        # A PNG: link previews (Reddit, Slack, iMessage) do not draw an SVG.
        card = esc(site.canonical(image or "/assets/og.png"))
        alt = esc(image_alt or site.name)
        head.append(f'<meta property="og:image" content="{card}">')
        head.append('<meta property="og:image:type" content="image/png">')
        head.append('<meta property="og:image:width" content="1200">')
        head.append('<meta property="og:image:height" content="630">')
        head.append(f'<meta property="og:image:alt" content="{alt}">')
        head.append(f'<meta name="twitter:image" content="{card}">')
        head.append(f'<meta name="twitter:image:alt" content="{alt}">')
    ld = structured_data(jsonld, body, path, site, noindex)
    if ld:
        head.append(ld)
    head += [
        '<meta name="color-scheme" content="light dark">',
        '<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">',
        '<link rel="icon" href="/assets/favicon-32.png" type="image/png" sizes="32x32">',
        '<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">',
        f'<link rel="alternate" type="application/atom+xml" title="{esc(site.name)}: what changed" href="{FEED_PATH}">',
    ]
    head += [f'<link rel="alternate" type="{esc(kind)}" href="{esc(href)}"{attrs(title=name)}>'
             for href, kind, name in alternates]
    head += [f'<link rel="preload" href="{fingerprint.url(f)}" as="font" type="font/woff2" crossorigin>' for f in FONT_PRELOADS]
    # The contour picture behind the page head: found by the stylesheet only, so it would arrive after
    # the first paint and, on a compact head, be the last thing painted (the page's largest paint).
    head.append(f'<link rel="preload" href="{fingerprint.url(CONTOURS)}" as="image" type="image/svg+xml">')
    head += [
        f'<link rel="stylesheet" href="{fingerprint.url("/assets/style.css")}">',
        # Sets the theme and unit preference before first paint (no inline scripts allowed).
        f'<script src="{fingerprint.url("/assets/prefs.js")}"></script>',
    ]
    # The page's one script. A page with a map does not load MapLibre (200 KB of script, 65 KB
    # of style) with the page: app.js loads these three files itself, a moment after the page has
    # loaded and never on a scroll or a touch, from the addresses it is given here.
    libs = {}
    if maps:
        libs = {"data-maplibre-css": MAPLIBRE_CSS, "data-maplibre-js": MAPLIBRE_JS}
        if outdoor:
            libs["data-contour-js"] = CONTOUR_JS
    libs = "".join(f' {name}="{fingerprint.url(src)}"' for name, src in libs.items())
    head.append(f'<script src="{fingerprint.url("/assets/app.js")}" defer{libs}></script>')
    head += [f'<script src="{esc(s)}" defer></script>' for s in scripts]
    data_block = json_block(data, "page-data") if data is not None else ""
    return f"""<!doctype html>
<html lang="en">
<head>
{chr(10).join(head)}
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>{skip_links(body)}
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
