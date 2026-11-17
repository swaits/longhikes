"""Small pieces the view pages share: a page heading with a breadcrumb, and rows of things that are not trails."""
import re

from . import words
from .markup import Markup, esc


def head(h1, lede_html, crumbs, *, kicker="", facts=()):
    """The page-head block. crumbs: [(text, href)] leading to this page; lede_html is HTML.
    facts: short facts (HTML) set as one quiet line under the lede."""
    items = "".join(f'<li><a href="{esc(h)}">{esc(t)}</a></li>' for t, h in crumbs)
    kick = f'<p class="kicker">{esc(kicker)}</p>' if kicker else ""
    line = "".join(f"<span>{f}</span>" for f in facts if str(f).strip())
    line = f'\n  <p class="page-head__facts">{line}</p>' if line else ""
    return f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol>{items}<li aria-current="page">{esc(h1)}</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text">
  {kick}<h1>{esc(h1)}</h1>
  <p class="page-head__lede">{lede_html}</p>{line}
  </div></header>
</div></div>"""


# The site sets no tables. A set of things (files, terms, changes, places) is shown as rows in the
# language of a trail's row: a name, a sentence where there is one, and a line of short facts.

# A cell longer than this (in characters of text) is a sentence of the row, not a fact in its line.
LONG_CELL = 60


def _text_len(html):
    return len(re.sub(r"<[^>]+>", "", str(html)).strip())


def plain_entry(name_html, *, text=(), facts=(), small=(), tag="", level=3, heading=True):
    """One row of something that is not a trail: name_html as a row's name, `tag` (HTML) above it as a
    route tag is, `text` (HTML paragraphs) as a row's sentence, `facts` (HTML) on a line as a row's
    facts are, `small` (HTML) as small print."""
    kicker = f'<p class="entry__kicker">{tag}</p>' if tag else ""
    h = f"h{level}" if heading else "p"
    paras = "".join(f'<p class="entry__desc">{t}</p>' for t in text if str(t).strip())
    line = "".join(f'<span>{f}</span>' for f in facts if str(f).strip())
    line = f'<p class="entry__meta">{line}</p>' if line else ""
    fine = " · ".join(str(x) for x in small if str(x).strip())
    fine = f'<p class="entry__small">{fine}</p>' if fine else ""
    return (f'<li class="entry entry--plain"><div class="entry__body">{kicker}'
            f'<{h} class="entry__name">{name_html}</{h}>{paras}{line}{fine}</div></li>')


def plain_list(items_html, label=""):
    aria = f' aria-label="{esc(label)}"' if label else ""
    return Markup(f'<ol class="entries entries--plain"{aria}>{"".join(items_html)}</ol>')


def rows_list(headers, rows, caption=""):
    """A set of things as rows: the first cell of each is its name; a long cell is its sentence; the
    short ones are its line of facts, each with its column's title."""
    items = []
    for row in rows:
        cells = [v if isinstance(v, Markup) else esc(v) for v in row]
        text, facts = [], []
        for label, cell in zip(headers[1:], cells[1:]):
            if not _text_len(cell):
                continue
            if _text_len(cell) > LONG_CELL:
                text.append(cell)
            else:
                facts.append(f'<span class="entry__label">{esc(label)}</span> {cell}')
        items.append(plain_entry(cells[0], text=text, facts=facts, heading=False))
    return plain_list(items, caption)


def table(headers, rows, *, caption="", numeric=(), row_heads=False, compare=False):
    """A set of things, shown as rows (rows_list): headers are the titles of the cells, rows lists of
    HTML cells (Markup, or text that is escaped). The other arguments are kept for the callers."""
    return rows_list(headers, rows, caption)


_TABLE = re.compile(r'(?:<div class="table-wrap">\s*)?<table\b[^>]*>(.*?)</table>(?:\s*</div>)?', re.S)
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<(th|td)\b[^>]*>(.*?)</\1>", re.S)
_CAPTION = re.compile(r"<caption\b[^>]*>(.*?)</caption>", re.S)


def untable(html):
    """html with every table in it set as rows (rows_list). For the pages written from Markdown and by
    hand, whose tables are plain: one head row, then body rows."""
    def one(m):
        inner = m.group(1)
        cap = _CAPTION.search(inner)
        rows = [[c[1].strip() for c in _CELL.findall(r)] for r in _ROW.findall(inner)]
        rows = [r for r in rows if r]
        if not rows:
            return ""
        head, body = rows[0], rows[1:]
        caption = re.sub(r"<[^>]+>", "", cap.group(1)) if cap else ""
        return str(rows_list(head, [[Markup(c) for c in r] for r in body], caption))
    return _TABLE.sub(one, str(html))


def trail_link(rec):
    from . import common
    return Markup(f'<a href="{esc(common.trail_path(rec))}">{common.name(rec)}</a>')


def ft_per_mile(m_per_km):
    """A climb rate as feet per mile and metres per kilometre, in the same unit pair as lengths."""
    ft_mi = m_per_km * words.M_PER_FT ** -1 * words.KM_PER_MI
    return Markup(f'<span class="len len--inline"><span class="len__mi">{esc(words.fmt_int(ft_mi))} ft per mile</span>'
                  f'<span class="len__km">{esc(words.fmt_int(m_per_km))} m per km</span></span>')


def append_nav(body, nav_html):
    """body with nav_html placed at the end of its last container (the page's closing </div>)."""
    text = str(body)
    i = text.rfind("</div>")
    return Markup(text[:i] + nav_html + text[i:]) if i >= 0 else Markup(text + nav_html)


def more_nav(path, extras):
    """A line of links to the other table, change and reference pages: extras is
    [(group, title, blurb, path, n)] as pages.py builds it for /lists/."""
    links = " · ".join(f'<a href="{esc(p)}">{esc(t)}</a>' for _, t, _, p, _ in extras if p != path)
    return (f'<nav class="region-nav" aria-label="More tables and reference pages">More pages: {links} · '
            f'<a href="/lists/">All lists</a></nav>') if links else ""
