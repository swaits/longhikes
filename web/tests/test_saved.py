"""Saved trails and the display switches in the header: what the generator writes.

The header carries the units switch and the theme menu on every page (and the
footer no longer does); every row of every list of trails, and every trail
page, has a Save button; /saved/ holds every row for app.js to show, is not
indexed and is not in the sitemap; nothing is inline. The behaviour itself
(localStorage, the link, the menu) is in app.js and was checked in browsers.
"""
import html
import os
import re
import subprocess
import sys
import unittest
from html.parser import HTMLParser

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import common, home, layout, records, saved, seo, site  # noqa: E402

OUT = os.path.join(WEB, ".cache", "test-site")


def setUpModule():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(WEB, "build.py"), "--out", OUT],
                   check=True, stdout=subprocess.DEVNULL)


def read_out(relpath):
    with open(os.path.join(OUT, *relpath.split("/")), encoding="utf-8") as f:
        return f.read()


def html_files():
    for base, _, names in os.walk(OUT):
        for n in names:
            if n.endswith(".html"):
                yield os.path.relpath(os.path.join(base, n), OUT).replace(os.sep, "/")


class Tree(HTMLParser):
    """Start tags with their attributes and the open elements above each one,
    and the text inside each <button>."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr",
            "path", "circle"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.tags = []        # (tag, attrs, [ancestor tags])
        self.buttons = []     # (attrs, text, [ancestor tags])
        self._button = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a, [t for t, _ in self.stack]))
        if tag == "button":
            self._button = [a, "", [t for t, _ in self.stack]]
        if tag not in self.VOID:
            self.stack.append((tag, a))

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag, dict(attrs), [t for t, _ in self.stack]))

    def handle_endtag(self, tag):
        if tag == "button" and self._button:
            self.buttons.append(tuple(self._button))
            self._button = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._button is not None:
            self._button[1] += data


def tree(doc):
    t = Tree()
    t.feed(doc)
    return t


class HeaderOnEveryPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = sorted(html_files())

    def test_every_page_has_the_switches_and_the_saved_link_in_its_header(self):
        self.assertGreater(len(self.files), 250)
        for rel in self.files:
            doc = read_out(rel)
            head = doc[doc.index('<header class="site-header">'):doc.index("</header>", doc.index('<header class="site-header">'))]
            self.assertIn('<div class="prefs js-only">', head, rel)
            self.assertIn('<input type="radio" name="units" value="mi" checked>', head, rel)
            self.assertIn('<input type="radio" name="units" value="km">', head, rel)
            self.assertIn('<details class="theme" data-theme-menu>', head, rel)
            for value in ("auto", "light", "dark"):
                self.assertIn(f'name="theme" value="{value}"', head, rel)
            self.assertIn('<li class="nav__saved js-only"><a href="/saved/"', head, rel)
            self.assertIn("data-saved-count hidden", head, rel)

    def test_the_footer_no_longer_has_the_switches(self):
        for rel in ("index.html", "about/index.html", "trails/pacific-crest/index.html"):
            doc = read_out(rel)
            foot = doc[doc.index('<footer class="site-footer">'):]
            self.assertNotIn('name="theme"', foot, rel)
            self.assertNotIn('name="units"', foot, rel)
            self.assertIn('<li class="js-only"><a href="/saved/">Saved trails</a></li>', foot, rel)

    def test_one_set_of_theme_radios_per_page(self):
        # Radios named "theme" form one group per page: only the header's.
        for rel in ("index.html", "saved/index.html", "trails/arizona/index.html"):
            self.assertEqual(read_out(rel).count('name="theme"'), 3, rel)

    def test_the_saved_link_is_current_on_the_saved_page_only(self):
        self.assertIn('<a href="/saved/" aria-current="page">', read_out("saved/index.html"))
        self.assertNotIn('<a href="/saved/" aria-current', read_out("index.html"))

    def test_nothing_inline(self):
        # The security policy allows no inline script, no <style> element and no
        # event-handler attribute; the switches and the Save buttons add none.
        for rel in self.files:
            doc = read_out(rel)
            self.assertNotIn("<style", doc, rel)
            inline = 0
            for tag, a, _ in tree(doc).tags:
                self.assertFalse([k for k in a if k.startswith("on")], f"{tag} in {rel}")
                if tag == "script" and not (a.get("src") or a.get("type") in ("application/json", "application/ld+json")):
                    inline += 1
            # The one inline script is the Google tag's data-layer setup, allowed by its hash.
            self.assertLessEqual(inline, 1, rel)
            if inline:
                self.assertIn("<script>" + layout.GOOGLE_TAG_INLINE + "</script>", doc, rel)

    def test_the_switches_name_what_they_do(self):
        prefs = layout.prefs()
        self.assertIn('<legend class="vh">Units</legend>', prefs)
        self.assertIn('<span class="vh">Miles and feet</span>', prefs)
        self.assertIn('<span class="vh">Kilometres and metres</span>', prefs)
        self.assertIn('<span class="vh">Theme: </span>', prefs)
        self.assertIn('<legend class="vh">Theme</legend>', prefs)
        self.assertIn('value="auto" checked', prefs)
        # Each icon is drawn inline, hidden from assistive technology.
        self.assertEqual(prefs.count("<svg"), 6)
        self.assertEqual(prefs.count('aria-hidden="true" focusable="false"'), 6)


class SaveButtonsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = records.load_records(ROOT)
        cls.names = {r["id"]: r["name"] for r in cls.records}

    def row_buttons(self, rel):
        return [(a, text, up) for a, text, up in tree(read_out(rel)).buttons if "save--row" in a.get("class", "")]

    def test_every_row_of_every_list_has_a_save_button(self):
        lists = ["index.html", "routes/index.html", "saved/index.html"]
        lists += [f"lists/{d}/index.html" for d in os.listdir(os.path.join(OUT, "lists"))
                  if os.path.isfile(os.path.join(OUT, "lists", d, "index.html"))]
        lists += [f"regions/{d}/index.html" for d in os.listdir(os.path.join(OUT, "regions"))
                  if os.path.isfile(os.path.join(OUT, "regions", d, "index.html"))]
        for rel in lists:
            doc = read_out(rel)
            rows = re.findall(r'<li class="entry" data-id="([^"]+)"', doc)
            buttons = self.row_buttons(rel)
            self.assertEqual([a["data-save"] for a, _, _ in buttons], rows, rel)
            for a, text, up in buttons:
                self.assertEqual(a["type"], "button", rel)
                self.assertEqual(a["aria-pressed"], "false", rel)
                self.assertNotIn("a", up, f"a Save button inside a link in {rel}")
                self.assertEqual(" ".join(text.split()), f"Save {self.names[a['data-save']]}", rel)

    def test_every_trail_page_has_a_save_button_by_its_actions(self):
        for rec in self.records:
            doc = read_out(f"trails/{rec['id']}/index.html")
            actions = doc[doc.index('<p class="trail-actions">'):doc.index("</p>", doc.index('<p class="trail-actions">'))]
            m = re.search(r'<button class="button button--quiet save save--page js-only" type="button" '
                          r'data-save="([^"]+)" aria-pressed="false">', actions)
            self.assertTrue(m, rec["id"])
            self.assertEqual(m.group(1), rec["id"])
            button = actions[m.start():actions.index("</button>", m.start())]
            visible = re.search(r'<span class="save__word" aria-hidden="true">([^<]*)</span>', button).group(1)
            name = html.unescape(re.sub(r"<[^>]+>", "", button[button.index('<span class="vh">'):]))
            self.assertEqual((visible, name), ("Save", f"Save {rec['name']}"), rec["id"])

    def test_the_star_follows_the_name_and_is_not_inside_its_link(self):
        rec = self.records[0]
        row = home.entry(rec)
        name_link_end = row.index("</a>", row.index('class="entry__name"'))
        self.assertLess(name_link_end, row.index('class="save save--row'))
        self.assertLess(row.index('class="save save--row'), row.index('class="entry__where"'))

    def test_names_are_escaped(self):
        rec = dict(self.records[0], id="x", name='A & B <i>')
        button = common.save_button(rec)
        self.assertIn("Save A &amp; B &lt;i&gt;", button)
        self.assertNotIn("<i>", button)


class SavedPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = records.load_records(ROOT)
        cls.doc = read_out("saved/index.html")

    def test_holds_every_trail_hidden_for_the_script_to_show(self):
        rows = re.findall(r'<li class="entry"( data-[^>]*)>', self.doc)
        self.assertEqual(len(rows), len(self.records))
        self.assertTrue(all(r.endswith(" hidden") for r in rows))
        self.assertIn('<ol class="entries" data-every-trail>', self.doc)
        self.assertIn("data-saved-total", self.doc)
        self.assertIn("data-saved-page", self.doc)

    def test_opens_in_the_order_saved(self):
        self.assertIn('data-default-sort="saved"', self.doc)
        self.assertIn('<option value="saved" selected>Order saved</option>', self.doc)
        # Only this page offers that order.
        self.assertNotIn('value="saved"', read_out("index.html"))

    def test_its_map_names_what_it_can_draw(self):
        fig = re.search(r'<figure class="mapfig[^"]*" data-map="overview"[^>]*>', self.doc).group(0)
        self.assertNotIn("data-ids=", fig)
        drawable = re.search(r'data-drawable="([^"]*)"', fig).group(1).split()
        self.assertEqual(drawable, home.drawable_ids(sorted(self.records, key=home.sort_name)))
        caption = self.doc[self.doc.index('<figcaption class="mapfig__caption">'):]
        self.assertNotRegex(caption[:caption.index("</figcaption>")], r"\d+ tracks")

    def test_link_controls_and_states_are_written(self):
        for hook in ("data-saved-share", "data-saved-url", 'data-copy="#saved-url"', 'data-copy-done="Link copied."',
                     "data-saved-from", "data-saved-merge", "data-saved-dropped", "data-saved-empty", "data-saved-none"):
            self.assertIn(hook, self.doc, hook)
        self.assertIn(">Copy link</button>", self.doc)
        self.assertIn("Save these</button>", self.doc)
        self.assertIn("Bookmark it, or send it to another device or another person", self.doc)
        self.assertIn('<a class="button button--primary" href="/">Find a trail</a>', self.doc)

    def test_says_it_needs_javascript(self):
        self.assertIn("Saved trails need JavaScript, which is off or blocked in this browser. "
                      '<a href="/">See every trail</a>.', self.doc)

    def test_not_indexed_and_not_in_the_sitemap(self):
        head = self.doc[:self.doc.index("</head>")]
        self.assertIn('<meta name="robots" content="noindex">', head)
        self.assertNotIn('rel="canonical"', head)
        self.assertNotIn('property="og:url"', head)
        self.assertNotIn("/saved/", read_out("sitemap.xml"))
        self.assertNotIn(saved.PATH, seo.all_paths(self.records, []))
        # Every other page keeps its canonical link and is indexable.
        other = read_out("about/index.html")
        self.assertIn('rel="canonical"', other)
        self.assertNotIn('name="robots"', other)

    def test_noindex_page_without_base_url(self):
        page = layout.layout("T", "", path="/saved/", noindex=True, site=site.Site("N", "T"))
        self.assertIn('<meta name="robots" content="noindex">', page)
        self.assertNotIn("canonical", page)

    def test_the_words_a_visitor_reads(self):
        text = re.sub(r"<[^>]+>", " ", self.doc[self.doc.index('<main id="main">'):self.doc.index('<ol class="entries"')])
        for word in ("favourite", "favorite", "bookmarks"):
            self.assertNotIn(word, text.lower())
        self.assertNotRegex(text, r"\bline\b")


class ScriptTest(unittest.TestCase):
    """app.js keeps its promises: one storage key, every access guarded, the events kept."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(WEB, "assets", "app.js"), encoding="utf-8") as f:
            cls.js = f.read()

    def test_one_key_every_access_guarded(self):
        self.assertIn("var SAVED_KEY = 'lh-saved';", self.js)
        for call in ("localStorage.getItem(SAVED_KEY)", "localStorage.setItem(SAVED_KEY", "localStorage.removeItem(SAVED_KEY)"):
            i = self.js.index(call)
            self.assertIn("try {", self.js[max(0, i - 120):i], call)
        self.assertIn("window.addEventListener('storage'", self.js)

    def test_the_events_still_fire(self):
        self.assertIn("document.dispatchEvent(new Event('olt:units'))", self.js)
        self.assertIn("document.dispatchEvent(new Event('olt:theme'))", self.js)
        self.assertIn("new CustomEvent('olt:saved'", self.js)

    def test_no_request_to_another_site_for_saving(self):
        part = self.js[self.js.index("1b. Saved trails"):self.js.index("/* 2. Maps")]
        self.assertNotIn("fetch(", part)
        self.assertNotIn("XMLHttpRequest", part)
        self.assertNotRegex(part, r"https?://")


if __name__ == "__main__":
    unittest.main()
