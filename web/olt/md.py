"""Markdown-to-HTML renderer for the site's own documents.

Covers what README.md, SOURCES.md, NOTICE.md, CONTRIBUTING.md, CHANGELOG.md
and docs/schema.md actually use, and little more.

Supported: ATX headings, paragraphs, unordered (``-``) and ordered (``1.``)
lists including nested lists and multi-line items, pipe tables with an
alignment row (``---``, ``---:``, ``:---:``), fenced code blocks with an
optional language, inline code, bold, italic, ``[text](url)`` links (also in
table cells; destinations may hold balanced parentheses or underscores), bare
``http(s)://`` URLs and ``<http(s)://...>`` autolinks, ``>`` block quotes,
``---``/``***``/``___`` horizontal rules, backslash escapes, and
``<!-- ... -->`` comments, which are dropped from the output.

Not supported: setext headings, reference-style links (a title after an
inline link's destination is accepted and dropped), images, footnotes,
strikethrough, task lists, indented code blocks, raw HTML passthrough
(anything but comments is escaped, never passed through), and emphasis
inside code spans or link destinations.
"""

import html as _html
import re

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]*(.*?)[ \t]*$")
_CLOSING_HASHES_RE = re.compile(r" +#+$")
_LIST_RE = re.compile(r"^([ ]*)([-+*]|\d+[.)])(?:[ \t]+|$)(.*)$")
_ALIGN_RE = re.compile(r"^:?-+:?$")
_TAG_RE = re.compile(r"<[^>]*>")
_LANG_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_AUTOLINK_RE = re.compile(r"^<(https?://[^<>\s]+)>")

_PUNCT = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")


def render(text, *, heading_offset=0, link_rewrite=None):
    """Render Markdown to an HTML fragment (no <html>/<body>).

    ``heading_offset`` shifts every heading down (``#`` becomes ``<h2>``
    with ``heading_offset=1``), capped at ``h6``. ``link_rewrite`` is an
    optional function called with each link's href, returning the href
    to use in the output, or None to drop the link and keep only its text.
    """
    slugs = {}
    lines = _strip_comments(text).split("\n")
    return "\n".join(_blocks(lines, heading_offset, link_rewrite, slugs))


def headings(text):
    """Return ``(level, plain text, slug id)`` for each heading, in order.

    The slug is the same id ``render`` puts on the heading element. Slugs
    are lower-case and hyphenated, and repeats get ``-2``, ``-3`` suffixes.
    """
    found = []
    slugs = {}
    in_fence = False
    for line in _strip_comments(text).split("\n"):
        if _fence_open(line) is not None or _fence_close(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        parsed = _parse_heading(line)
        if parsed is None:
            continue
        level, raw = parsed
        plain = _plain(raw)
        found.append((level, plain, _slugify(plain, slugs)))
    return found


def split_sections(text, level=2):
    """Split Markdown into ``(heading text, Markdown body)`` sections.

    A new section starts at each ATX heading with exactly ``level``
    hashes; its body is the raw Markdown under it, up to the next heading
    of that level or shallower (deeper headings stay in the body). Text
    before the first such heading is not part of any section.
    """
    if not 1 <= level <= 6:
        raise ValueError("level must be 1..6")
    sections = []
    title = None
    body = []
    in_fence = False
    for line in _strip_comments(text).split("\n"):
        if _fence_open(line) is not None or _fence_close(line):
            in_fence = not in_fence
            if title is not None:
                body.append(line)
            continue
        parsed = _parse_heading(line) if not in_fence else None
        if parsed is not None and parsed[0] <= level:
            if title is not None:
                sections.append((title, _trim(body)))
            if parsed[0] == level:
                title = _plain(parsed[1])
                body = []
            else:
                title = None
                body = []
        elif title is not None:
            body.append(line)
    if title is not None:
        sections.append((title, _trim(body)))
    return sections


def _trim(lines):
    while lines and not lines[0].strip():
        del lines[0]
    while lines and not lines[-1].strip():
        del lines[-1]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Block layer
# ---------------------------------------------------------------------------

def _blocks(lines, offset, link_rewrite, slugs):
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if _fence_open(line) is not None:
            html, i = _take_fence(lines, i)
            out.append(html)
        elif _parse_heading(line) is not None:
            level, raw = _parse_heading(line)
            plain = _plain(raw)
            tag = min(6, level + offset)
            slug = _slugify(plain, slugs)
            out.append(f"<h{tag} id=\"{slug}\">"
                       f"{_inline(raw, link_rewrite)}</h{tag}>")
            i += 1
        elif _is_hr(line):
            out.append("<hr>")
            i += 1
        elif _parse_quote(line) is not None:
            quoted = []
            while i < n and _parse_quote(lines[i]) is not None:
                quoted.append(_parse_quote(lines[i]))
                i += 1
            inner = _blocks(quoted, offset, link_rewrite, slugs)
            if inner:
                out.append("<blockquote>\n" + "\n".join(inner)
                           + "\n</blockquote>")
            else:
                out.append("<blockquote>\n</blockquote>")
        elif _is_list_start(line):
            html, i = _parse_list(lines, i, offset, link_rewrite, slugs)
            out.append(html)
        elif _table_at(lines, i) is not None:
            html, i = _take_table(lines, i, link_rewrite)
            out.append(html)
        else:
            buf = [line]
            i += 1
            while i < n and not _starts_block(lines, i):
                buf.append(lines[i])
                i += 1
            out.append("<p>" + _inline("\n".join(buf).strip(),
                                      link_rewrite) + "</p>")
    return out


def _starts_block(lines, i):
    line = lines[i]
    if not line.strip():
        return True
    if _fence_open(line) is not None:
        return True
    if _parse_heading(line) is not None:
        return True
    if _is_hr(line):
        return True
    if _parse_quote(line) is not None:
        return True
    if _is_list_start(line):
        return True
    if _table_at(lines, i) is not None:
        return True
    return False


def _parse_heading(line):
    """Return ``(level, raw text)`` for an ATX heading, else None."""
    body = line.lstrip(" ")
    if len(line) - len(body) > 3 or not body.startswith("#"):
        return None
    match = _HEADING_RE.match(body)
    if match is None:
        return None
    hashes, rest = match.group(1), match.group(2)
    if body[len(hashes):len(hashes) + 1] not in ("", " ", "\t"):
        return None
    rest = _CLOSING_HASHES_RE.sub("", rest).strip()
    return (len(hashes), rest)


def _fence_open(line):
    """Return the info string for a fence opener, else None."""
    body = line.lstrip(" ")
    if len(line) - len(body) > 3 or not body.startswith("```"):
        return None
    if body[3:4] == "`":
        return None
    return body[3:].strip()


def _fence_close(line):
    stripped = line.strip()
    return (stripped.startswith("```")
            and all(ch in " \t" for ch in stripped[3:]))


def _take_fence(lines, i):
    info = _fence_open(lines[i])
    lang = info.split()[0] if info.split() else ""
    buf = []
    i += 1
    while i < len(lines) and not _fence_close(lines[i]):
        buf.append(lines[i])
        i += 1
    if i < len(lines):
        i += 1
    if lang and _LANG_RE.match(lang):
        open_tag = f'<pre><code class="language-{lang}">'
    else:
        open_tag = "<pre><code>"
    return open_tag + _html.escape("\n".join(buf)) + "</code></pre>", i


def _is_hr(line):
    stripped = line.strip()
    if len(stripped) < 3 or stripped[0] not in "*-_":
        return False
    char = stripped[0]
    return (stripped.count(char) >= 3
            and all(ch in (char, " ", "\t") for ch in stripped))


def _parse_quote(line):
    """Return the line's quote content, else None."""
    body = line.lstrip(" ")
    if len(line) - len(body) > 3 or not body.startswith(">"):
        return None
    rest = body[1:]
    if rest.startswith((" ", "\t")):
        rest = rest[1:]
    return rest


def _is_list_start(line):
    match = _LIST_RE.match(line)
    return match is not None and len(match.group(1)) <= 3


def _parse_list(lines, i, offset, link_rewrite, slugs):
    first = _LIST_RE.match(lines[i])
    base = len(first.group(1))
    ordered = first.group(2)[0].isdigit()
    start = int(first.group(2)[:-1]) if ordered else 1
    items = []
    loose = False
    n = len(lines)
    while i < n:
        match = _LIST_RE.match(lines[i])
        if (match is None or len(match.group(1)) != base
                or (match.group(2)[0].isdigit() != ordered)):
            break
        content_indent = base + len(match.group(2)) + 1
        item = [match.group(3)]
        i += 1
        while i < n:
            line = lines[i]
            if not line.strip():
                end = i
                while end < n and not lines[end].strip():
                    end += 1
                if end >= n:
                    i = end
                    break
                peek = _LIST_RE.match(lines[end])
                peek_indent = len(lines[end]) - len(lines[end].lstrip(" "))
                same_item = peek is not None and peek.group(2)[0].isdigit() == ordered and peek_indent == base
                if same_item or peek_indent >= content_indent:
                    loose = True
                    item.append("")
                    i = end
                else:
                    break
                continue
            inner = _LIST_RE.match(line)
            indent = len(line) - len(line.lstrip(" "))
            if (inner is not None and indent == base
                    and inner.group(2)[0].isdigit() == ordered):
                break
            if indent >= content_indent:
                item.append(line[content_indent:])
                i += 1
            else:
                break
        while item and not item[-1].strip():
            item.pop()
        items.append(item)
    rendered = []
    for item in items:
        sub = _blocks(item, offset, link_rewrite, slugs)
        if (not loose and sub and sub[0].startswith("<p>")
                and sub[0].endswith("</p>")):
            sub = [sub[0][len("<p>"):-len("</p>")]] + sub[1:]
        rendered.append("<li>" + "\n".join(sub) + "</li>" if sub else "<li></li>")
    if ordered and start != 1:
        open_tag, close_tag = f'<ol start="{start}">', "</ol>"
    elif ordered:
        open_tag, close_tag = "<ol>", "</ol>"
    else:
        open_tag, close_tag = "<ul>", "</ul>"
    return open_tag + "\n" + "\n".join(rendered) + "\n" + close_tag, i


def _split_cells(line):
    """Split a table row into cell segment lists.

    Each cell is a list of ``(is_code, text)`` segments. Pipes inside
    code spans or escaped as ``\\|`` never split the cell.
    """
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    cells = []
    current = []
    for is_code, chunk in _split_code(text):
        if is_code:
            current.append((True, chunk))
        else:
            pieces = re.split(r"(?<!\\)\|", chunk)
            current.append((False, pieces[0]))
            for piece in pieces[1:]:
                cells.append(current)
                current = [(False, piece)]
    cells.append(current)
    for cell in cells:
        if cell and not cell[0][0]:
            cell[0] = (False, cell[0][1].lstrip(" \t"))
        if cell and not cell[-1][0]:
            cell[-1] = (False, cell[-1][1].rstrip(" \t"))
    return cells


def _render_cell(cell, link_rewrite):
    parts = []
    for is_code, chunk in cell:
        if is_code:
            parts.append("<code>" + _html.escape(chunk) + "</code>")
        else:
            parts.append(_inline_raw(chunk, link_rewrite))
    return "".join(parts)


def _align(cell):
    text = cell.strip()
    if text.startswith(":") and text.endswith(":") and len(text) > 2:
        return "center"
    if text.endswith(":"):
        return "right"
    return "left"


def _table_at(lines, i):
    """Return the alignment row's cells if a table starts here."""
    if "|" not in lines[i] or i + 1 >= len(lines):
        return None
    cells = _split_cells(lines[i + 1])
    if not cells:
        return None
    raws = []
    for cell in cells:
        raws.append("".join(chunk for _, chunk in cell))
    if any(not _ALIGN_RE.match(raw.strip()) for raw in raws):
        return None
    return raws


def _take_table(lines, i, link_rewrite):
    header = _split_cells(lines[i])
    aligns = [_align("".join(chunk for _, chunk in cell))
              for cell in _split_cells(lines[i + 1])]
    width = max(len(header), len(aligns))
    while len(header) < width:
        header.append([(False, "")])
    while len(aligns) < width:
        aligns.append("left")

    def row(cells, tag):
        out = []
        scope = ' scope="col"' if tag == "th" else ""
        for pos in range(width):
            cell = cells[pos] if pos < len(cells) else [(False, "")]
            cls = ' class="num"' if aligns[pos] == "right" else ""
            out.append(f"<{tag}{scope}{cls}>" + _render_cell(cell, link_rewrite)
                       + f"</{tag}>")
        return "<tr>" + "".join(out) + "</tr>"

    head = row(header, "th")
    body_rows = []
    i += 2
    while i < len(lines) and lines[i].strip() and "|" in lines[i]:
        body_rows.append(row(_split_cells(lines[i]), "td"))
        i += 1
    html = "<table>\n<thead>\n" + head + "\n</thead>"
    if body_rows:
        html += "\n<tbody>\n" + "\n".join(body_rows) + "\n</tbody>"
    return html + "\n</table>", i


# ---------------------------------------------------------------------------
# Comments, slugs, plain text
# ---------------------------------------------------------------------------

def _strip_comments(text):
    """Drop ``<!-- ... -->`` spans; fenced code blocks are left alone."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out = []
    in_fence = False
    in_comment = False
    for line in text.split("\n"):
        if not in_comment and (_fence_open(line) is not None
                               or _fence_close(line)):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        line, in_comment = _strip_line_comment(line, in_comment)
        out.append(line)
    return "\n".join(out)


def _strip_line_comment(line, in_comment):
    if in_comment:
        end = line.find("-->")
        if end < 0:
            return "", True
        line = line[end + 3:]
        in_comment = False
    while True:
        start = line.find("<!--")
        if start < 0:
            return line, False
        end = line.find("-->", start + 4)
        if end < 0:
            return line[:start], True
        line = line[:start] + line[end + 3:]


def _plain(raw):
    """Inline formatting stripped to plain text (for headings)."""
    return _html.unescape(_TAG_RE.sub("", _inline(raw, None)))


def _slugify(plain, slugs):
    base = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    if not base:
        base = "section"
    count = slugs.get(base, 0) + 1
    slugs[base] = count
    return base if count == 1 else f"{base}-{count}"


# ---------------------------------------------------------------------------
# Inline layer
# ---------------------------------------------------------------------------

def _inline(text, link_rewrite):
    parts = []
    for is_code, chunk in _split_code(text):
        if is_code:
            code = chunk
            if len(code) > 2 and code[0] in " \t" and code[-1] in " \t" and code.strip(" \t"):
                code = code[1:-1]
            parts.append("<code>" + _html.escape(code) + "</code>")
        else:
            parts.append(_inline_raw(chunk, link_rewrite))
    return "".join(parts)


def _split_code(text):
    """Split text into ``(is_code, chunk)`` parts at backtick spans."""
    parts = []
    buf = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "`":
            buf.append(text[i])
            i += 1
            continue
        end = i
        while end < n and text[end] == "`":
            end += 1
        run = end - i
        close = _find_close(text, end, run)
        if close < 0:
            buf.append(text[i:end])
            i = end
        else:
            if buf:
                parts.append((False, "".join(buf)))
                buf = []
            parts.append((True, text[end:close]))
            i = close + run
    if buf:
        parts.append((False, "".join(buf)))
    return parts


def _find_close(text, start, run):
    tick = "`" * run
    pos = text.find(tick, start)
    while pos >= 0:
        prev_is_tick = pos > 0 and text[pos - 1] == "`"
        next_is_tick = pos + run < len(text) and text[pos + run] == "`"
        if not prev_is_tick and not next_is_tick:
            return pos
        pos = text.find(tick, pos + 1)
    return -1


def _inline_raw(text, link_rewrite):
    out = []
    i = 0
    n = len(text)
    while i < n:
        char = text[i]
        if char == "\\" and i + 1 < n and text[i + 1] in _PUNCT:
            out.append(_html.escape(text[i + 1]))
            i += 2
        elif char == "[":
            html, i = _parse_link(text, i, link_rewrite)
            out.append(html)
        elif char == "<":
            html, i = _parse_angle(text, i, link_rewrite)
            out.append(html)
        elif ((text.startswith("http://", i) or text.startswith("https://", i))
                and (i == 0 or text[i - 1] in " \t\n('\"")):
            html, i = _parse_bare(text, i, link_rewrite)
            out.append(html)
        elif char in "*_":
            html, i = _parse_emph(text, i, link_rewrite)
            out.append(html)
        elif char == "&":
            out.append("&amp;")
            i += 1
        elif char == ">":
            out.append("&gt;")
            i += 1
        else:
            out.append(_html.escape(char))
            i += 1
    return "".join(out)


def _parse_link(text, i, link_rewrite):
    """Parse ``[label](destination)`` at ``text[i] == '['``."""
    close = text.find("]", i + 1)
    if close < 0 or close + 1 >= len(text) or text[close + 1] != "(":
        return "[", i + 1
    pos = close + 2
    while pos < len(text) and text[pos] in " \t":
        pos += 1
    if pos < len(text) and text[pos] == "<":
        end = text.find(">", pos + 1)
        if end < 0:
            return "[", i + 1
        dest, pos = text[pos + 1:end], end + 1
    else:
        start = pos
        depth = 0
        while pos < len(text):
            char = text[pos]
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            elif char in " \t\n" and depth == 0:
                break
            pos += 1
        dest = text[start:pos]
    end = pos
    while end < len(text) and text[end] in " \t":
        end += 1
    if end < len(text) and text[end] in "\"'(":
        quote = ")" if text[end] == "(" else text[end]
        title_end = text.find(quote, end + 1)
        if title_end < 0:
            return "[", i + 1
        end = title_end + 1
        if end >= len(text) or text[end] != ")":
            return "[", i + 1
        pos = end
    if pos >= len(text) or text[pos] != ")":
        return "[", i + 1
    href = dest.strip()
    if not href:
        return "[", i + 1
    if link_rewrite is not None:
        href = link_rewrite(href)
    inner = _inline(text[i + 1:close], link_rewrite)
    if href is None:
        return inner, pos + 1
    return (f'<a href="{_html.escape(href, quote=True)}">{inner}</a>',
            pos + 1)


def _parse_angle(text, i, link_rewrite):
    """Parse ``<https://...>`` autolinks; anything else is escaped."""
    match = _AUTOLINK_RE.match(text[i:])
    if match is None:
        return "&lt;", i + 1
    url = match.group(1)
    href = link_rewrite(url) if link_rewrite is not None else url
    return _anchor(href, url), i + match.end()


def _parse_bare(text, i, link_rewrite):
    end = i
    while end < len(text) and text[end] not in " \t\n<>":
        end += 1
    url = text[i:end].rstrip(".,;:!?")
    while url.endswith(")") and url.count("(") < url.count(")"):
        url = url[:-1]
    href = link_rewrite(url) if link_rewrite is not None else url
    return _anchor(href, url), i + len(url)


def _anchor(href, text):
    """``<a>`` around escaped text, or the text alone when href is None."""
    if href is None:
        return _html.escape(text)
    return (f'<a href="{_html.escape(href, quote=True)}">'
            f"{_html.escape(text)}</a>")


def _can_open(char, prev, nxt):
    if not nxt or nxt in " \t\n":
        return False
    return not (char == "_" and prev.isalnum() and nxt.isalnum())


def _can_close(char, prev, nxt):
    if not prev or prev in " \t\n":
        return False
    return not (char == "_" and prev.isalnum() and nxt.isalnum())


def _find_closer(text, pos, char, run_len):
    i = pos
    n = len(text)
    while i < n:
        if text[i] != char:
            i += 1
            continue
        end = i
        while end < n and text[end] == char:
            end += 1
        run = end - i
        if run >= run_len and (run_len == 2 or run == 1):
            prev = text[i - 1] if i > 0 else ""
            nxt = text[end] if end < n else ""
            if _can_close(char, prev, nxt):
                return i
        i = end
    return -1


def _parse_emph(text, i, link_rewrite):
    """Parse ``**bold**`` or ``*italic*`` at a ``*``/``_`` run."""
    char = text[i]
    end = i
    while end < len(text) and text[end] == char:
        end += 1
    run = end - i
    prev = text[i - 1] if i > 0 else ""
    for run_len, tag in ((2, "strong"), (1, "em")) if run >= 2 else ((1, "em"),):
        if run_len == 2 and run < 2:
            continue
        nxt = text[i + run_len] if i + run_len < len(text) else ""
        if not _can_open(char, prev, nxt):
            continue
        close = _find_closer(text, i + run_len, char, run_len)
        if close < 0:
            continue
        inner = _inline_raw(text[i + run_len:close], link_rewrite)
        if not inner.strip():
            continue
        return f"<{tag}>{inner}</{tag}>", close + run_len
    return _html.escape(text[i:end]), end
