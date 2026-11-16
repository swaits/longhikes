"""Small pieces the new view pages share: a page heading with a breadcrumb, a table, a ranked row."""
from . import words
from .markup import Markup, esc


def head(h1, lede_html, crumbs, *, kicker=""):
    """The page-head block. crumbs: [(text, href)] leading to this page; lede_html is HTML."""
    items = "".join(f'<li><a href="{esc(h)}">{esc(t)}</a></li>' for t, h in crumbs)
    kick = f'<p class="kicker">{esc(kicker)}</p>' if kicker else ""
    return f"""<div class="page-head"><div class="container">
  <nav class="breadcrumb" aria-label="Breadcrumb"><ol>{items}<li aria-current="page">{esc(h1)}</li></ol></nav>
  <header class="titleblock"><div class="titleblock__text">
  {kick}<h1>{esc(h1)}</h1>
  <p class="page-head__lede">{lede_html}</p>
  </div></header>
</div></div>"""


def table(headers, rows, *, caption="", numeric=(), row_heads=False):
    """A table in the site's table wrapper. headers: column titles; rows: lists of HTML cells
    (Markup, or text that is escaped); numeric: column numbers set at the end of the cell;
    row_heads: the first cell of each row is a row heading."""
    def cell(i, value, head=False):
        text = value if isinstance(value, Markup) else esc(value)
        cls = ' class="num"' if i in numeric else ""
        if head:
            return f'<th scope="row"{cls}>{text}</th>'
        return f"<td{cls}>{text}</td>"
    cap = f'<caption class="vh">{esc(caption)}</caption>' if caption else ""
    num = ' class="num"'
    head = "".join(f'<th scope="col"{num if i in numeric else ""}>{esc(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(cell(i, v, head=row_heads and i == 0) for i, v in enumerate(row)) + "</tr>"
        for row in rows)
    return Markup(f'<div class="table-wrap"><table>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


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
