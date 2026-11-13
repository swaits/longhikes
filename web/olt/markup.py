"""Small HTML helpers: escaping, attributes, joining. Standard library only.

Write page templates as f-strings and pass every value that comes from data
through esc() (text and attribute values alike). Strings that are already HTML
are Markup; esc() leaves them alone, so helpers can return Markup and be
dropped into other templates without double escaping.
"""
import html
import json


class Markup(str):
    """A string that is already HTML and must not be escaped again."""


def esc(value):
    """Escape text for HTML text or a double-quoted attribute value."""
    if isinstance(value, Markup):
        return value
    if value is None:
        return Markup("")
    return Markup(html.escape(str(value), quote=True))


def attrs(**kw):
    """Attribute string: attrs(class_="a", data_id="x", hidden=True) -> ' class="a" data-id="x" hidden'.

    A trailing underscore is dropped (class_ -> class) and other underscores
    become hyphens (aria_label -> aria-label). None and False are left out.
    """
    out = []
    for key, value in kw.items():
        if value is None or value is False:
            continue
        name = key.rstrip("_").replace("_", "-")
        out.append(f" {name}" if value is True else f' {name}="{esc(value)}"')
    return Markup("".join(out))


def join(items, sep=""):
    """Join pieces of HTML; plain strings among them are escaped."""
    return Markup(esc(sep).join(esc(i) for i in items if i not in (None, "")))


def link(href, text, **kw):
    """<a href=...>text</a>, with text escaped unless it is Markup."""
    return Markup(f"<a{attrs(href=href, **kw)}>{esc(text)}</a>")


def json_block(obj, id_):
    """A non-executed <script type="application/json"> block (allowed by the site's CSP)."""
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return Markup(f'<script type="application/json" id="{esc(id_)}">{text}</script>')
