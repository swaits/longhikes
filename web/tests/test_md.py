import html.parser
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from olt import md  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DOCS = ["README.md", "SOURCES.md", "NOTICE.md",
        "CONTRIBUTING.md", "CHANGELOG.md", "docs/schema.md"]


def read_doc(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


class TagBalance(html.parser.HTMLParser):
    VOID = {"hr", "br", "img", "meta", "link", "input", "col"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        self.stack.append(tag)
        if tag == "a":
            self.hrefs.append(dict(attrs).get("href", ""))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append("unmatched </%s>, open=%r" % (tag, self.stack))


def check_well_formed(html):
    checker = TagBalance()
    checker.feed(html)
    checker.close()
    return checker


class TableCounter(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.counts = []
        self.in_tbody = False

    def handle_starttag(self, tag, attrs):
        if tag == "tbody":
            self.in_tbody = True
            self.counts.append(0)
        elif tag == "tr" and self.in_tbody:
            self.counts[-1] += 1

    def handle_endtag(self, tag):
        if tag == "tbody":
            self.in_tbody = False


class HeadingsTest(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(md.render("# One"), '<h1 id="one">One</h1>')
        self.assertEqual(md.render("### Three"), '<h3 id="three">Three</h3>')
        self.assertEqual(md.render("###### Six"), '<h6 id="six">Six</h6>')

    def test_offset(self):
        self.assertEqual(md.render("# One", heading_offset=1),
                         '<h2 id="one">One</h2>')
        self.assertEqual(md.render("### Three", heading_offset=2),
                         '<h5 id="three">Three</h5>')

    def test_offset_capped_at_h6(self):
        self.assertTrue(md.render("### Three", heading_offset=9)
                        .startswith("<h6 "))
        self.assertTrue(md.render("# One", heading_offset=5)
                        .startswith("<h6 "))

    def test_heading_without_space_is_paragraph(self):
        self.assertEqual(md.render("#nospace"), "<p>#nospace</p>")

    def test_headings_values(self):
        self.assertEqual(md.headings("# Hello, World!\n\n## B *c*"),
                         [(1, "Hello, World!", "hello-world"),
                          (2, "B c", "b-c")])

    def test_duplicate_slugs_numbered(self):
        self.assertEqual(
            [slug for _, _, slug in md.headings("# A\n# A\n# A")],
            ["a", "a-2", "a-3"])

    def test_render_uses_same_slugs_as_headings(self):
        text = "# Repeat\n\n# Repeat\n"
        html = md.render(text)
        for _, _, slug in md.headings(text):
            self.assertIn('id="%s"' % slug, html)

    def test_heading_inline_markup_excluded_from_slug(self):
        self.assertEqual(md.headings("## Use `code` here"),
                         [(2, "Use code here", "use-code-here")])


class SectionsTest(unittest.TestCase):
    def test_basic_split(self):
        self.assertEqual(
            md.split_sections("# Title\n\nintro\n\n## One\nbody one\n## Two\nbody two"),
            [("One", "body one"), ("Two", "body two")])

    def test_preamble_excluded(self):
        sections = md.split_sections("# Title\n\nintro\n\n## One\nbody\n")
        self.assertEqual(sections, [("One", "body")])

    def test_subheadings_stay_in_body(self):
        sections = md.split_sections("## One\ntext\n### Sub\nmore\n## Two\nend\n")
        self.assertEqual(sections, [("One", "text\n### Sub\nmore"),
                                    ("Two", "end")])

    def test_default_level_is_two(self):
        self.assertEqual(len(md.split_sections("# T\n\n# U")), 0)
        self.assertEqual(len(md.split_sections("# T\n\n## U")), 1)

    def test_bad_level_rejected(self):
        with self.assertRaises(ValueError):
            md.split_sections("text", level=0)
        with self.assertRaises(ValueError):
            md.split_sections("text", level=7)

    def test_readme_inclusion_rule(self):
        sections = dict(md.split_sections(read_doc("README.md")))
        self.assertIn("Inclusion rule", sections)
        self.assertIn("A long trail here is a named, continuous walking route",
                      sections["Inclusion rule"])
        self.assertEqual(len(sections), 11)


class ParagraphsTest(unittest.TestCase):
    def test_simple_paragraph(self):
        self.assertEqual(md.render("Hello world."), "<p>Hello world.</p>")

    def test_blocks_separated(self):
        self.assertEqual(md.render("One.\n\nTwo."),
                         "<p>One.</p>\n<p>Two.</p>")

    def test_raw_html_is_escaped(self):
        html = md.render("Use <id>/trail.toml and <n> trails.")
        self.assertIn("&lt;id&gt;/trail.toml", html)
        self.assertIn("&lt;n&gt;", html)
        self.assertNotIn("<id>", html)

    def test_ampersand_escaped(self):
        self.assertIn("a &amp; b", md.render("a & b"))


class ListsTest(unittest.TestCase):
    def test_unordered(self):
        self.assertEqual(md.render("- a\n- b"),
                         "<ul>\n<li>a</li>\n<li>b</li>\n</ul>")

    def test_ordered(self):
        self.assertEqual(md.render("1. one\n2. two"),
                         "<ol>\n<li>one</li>\n<li>two</li>\n</ol>")

    def test_ordered_paren_marker(self):
        self.assertIn("<ol>", md.render("1) one\n2) two"))

    def test_nested(self):
        html = md.render("- a\n  - b\n- c")
        self.assertIn("<li>a\n<ul>\n<li>b</li>\n</ul></li>", html)

    def test_multiline_item_joined(self):
        html = md.render("1. first line\n   second line\n2. next")
        self.assertIn("<li>first line\nsecond line</li>", html)

    def test_loose_list_keeps_paragraphs(self):
        html = md.render("- a\n\n- b")
        self.assertIn("<li><p>a</p></li>", html)
        self.assertIn("<li><p>b</p></li>", html)

    def test_markup_inside_items(self):
        html = md.render("- `code` and **bold**")
        self.assertIn("<li><code>code</code> and <strong>bold</strong></li>",
                      html)


class TablesTest(unittest.TestCase):
    def test_header_and_body(self):
        html = md.render("| a | b |\n| --- | --- |\n| 1 | 2 |")
        self.assertIn("<thead>", html)
        self.assertIn("<tbody>", html)
        self.assertIn('<th scope="col">a</th>', html)
        self.assertIn("<td>1</td>", html)

    def test_right_align_gets_num_class(self):
        html = md.render("| a | b |\n| --- | ---: |\n| 1 | 2 |")
        self.assertIn('<th scope="col" class="num">b</th>', html)
        self.assertIn('<td class="num">2</td>', html)
        self.assertIn('<th scope="col">a</th>', html)

    def test_no_inline_styles(self):
        html = md.render("| a |\n| ---: |\n| 1 |")
        self.assertNotIn("style=", html)

    def test_needs_alignment_row(self):
        self.assertNotIn("<table>", md.render("| a | b |\n| 1 | 2 |"))

    def test_links_and_parens_urls_in_cells(self):
        html = md.render(
            "| T |\n| --- |\n"
            "| [source page](https://e.com/POHE_Trail_(Public_NPMap)/0) |")
        self.assertIn('<a href="https://e.com/POHE_Trail_(Public_NPMap)/0">'
                      "source page</a>", html)

    def test_pipe_in_code_does_not_split(self):
        html = md.render("| a | b |\n| --- | --- |\n| `x|y` | 2 |")
        self.assertEqual(html.count("<td>"), 2)
        self.assertIn("<code>x|y</code>", html)

    def test_escaped_pipe_does_not_split(self):
        html = md.render("| a |\n| --- |\n| x\\|y |")
        self.assertEqual(html.count("<td>"), 1)
        self.assertIn("x|y", html)

    def test_underscores_in_cell_urls_untouched(self):
        html = md.render("| a |\n| --- |\n"
                         "| [p](https://e.com/a_b_c/0) |")
        self.assertIn('href="https://e.com/a_b_c/0"', html)


class CodeTest(unittest.TestCase):
    def test_fenced_with_language(self):
        html = md.render("```toml\nid = \"x\"\n```")
        self.assertEqual(html, '<pre><code class="language-toml">'
                               'id = &quot;x&quot;</code></pre>')

    def test_fenced_without_language(self):
        html = md.render("```\nplain\n```")
        self.assertEqual(html, "<pre><code>plain</code></pre>")

    def test_fence_content_not_parsed(self):
        html = md.render("```text\n**no** [link](https://e.com) `x`\n```")
        self.assertNotIn("<strong>", html)
        self.assertNotIn("<a ", html)
        self.assertIn("**no** [link](https://e.com) `x`", html)

    def test_fence_content_escaped(self):
        self.assertIn("&lt;id&gt;", md.render("```\n<id>\n```"))

    def test_inline_code(self):
        self.assertEqual(md.render("Use `trail.toml` here."),
                         "<p>Use <code>trail.toml</code> here.</p>")

    def test_code_not_parsed(self):
        html = md.render("`*not* [em](https://e.com/x_(y))`")
        self.assertNotIn("<em>", html)
        self.assertNotIn("<a ", html)


class InlineTest(unittest.TestCase):
    def test_bold(self):
        self.assertEqual(md.render("a **bold** b"),
                         "<p>a <strong>bold</strong> b</p>")

    def test_italic(self):
        self.assertEqual(md.render("a *italic* b"),
                         "<p>a <em>italic</em> b</p>")

    def test_italic_in_bold(self):
        self.assertEqual(md.render("**a *b* c**"),
                         "<p><strong>a <em>b</em> c</strong></p>")

    def test_unmatched_markers_literal(self):
        self.assertEqual(md.render("a ** b"), "<p>a ** b</p>")
        self.assertEqual(md.render("a * b"), "<p>a * b</p>")

    def test_intraword_underscore_literal(self):
        self.assertIn("agol_flt", md.render("hosts its line as 'agol_flt'"))

    def test_link(self):
        self.assertEqual(md.render("[text](https://e.com/x)"),
                         '<p><a href="https://e.com/x">text</a></p>')

    def test_link_rewrite(self):
        html = md.render("[schema](docs/schema.md)",
                         link_rewrite=lambda h: "/data/schema/")
        self.assertIn('<a href="/data/schema/">schema</a>', html)

    def test_link_rewrite_none_keeps_the_text_only(self):
        drop = lambda h: None if h.startswith("tools/") else h  # noqa: E731
        html = md.render("See [the tools](tools/build_index.py) and "
                         "[schema](/data/schema/), <https://e.com/a>.",
                         link_rewrite=lambda h: None if h != "/data/schema/" else h)
        self.assertEqual(html, '<p>See the tools and <a href="/data/schema/">schema</a>, '
                               'https://e.com/a.</p>')
        html = md.render("| a |\n| --- |\n| [*x* y](tools/x.py) https://e.com/b |",
                         link_rewrite=drop)
        self.assertIn("<td><em>x</em> y ", html)
        self.assertIn('<a href="https://e.com/b">https://e.com/b</a>', html)
        self.assertNotIn("tools/", html)

    def test_link_url_with_parens(self):
        html = md.render("[p](https://e.com/a_(b)_/c)")
        self.assertIn('href="https://e.com/a_(b)_/c"', html)

    def test_bare_url(self):
        html = md.render("see https://www.example.com/x for more")
        self.assertIn('<a href="https://www.example.com/x">'
                      "https://www.example.com/x</a>", html)

    def test_angle_autolink(self):
        self.assertIn('<a href="https://e.com/x">https://e.com/x</a>',
                      md.render("<https://e.com/x>"))

    def test_non_link_angle_escaped(self):
        html = md.render("a <n> b")
        self.assertIn("&lt;n&gt;", html)
        self.assertNotIn("<a ", html)

    def test_escape(self):
        html = md.render("a \\* b \\` c")
        self.assertIn("a * b ` c", html)
        self.assertNotIn("<em>", html)

    def test_comment_dropped(self):
        self.assertEqual(md.render("a <!-- note --> b"), "<p>a  b</p>")

    def test_comment_lines_dropped(self):
        html = md.render("<!-- BEGIN -->\n\ntext\n\n<!-- END -->")
        self.assertEqual(html, "<p>text</p>")
        self.assertNotIn("<!--", html)

    def test_comment_inside_fence_kept(self):
        html = md.render("```\n<!-- keep -->\n```")
        self.assertIn("&lt;!-- keep --&gt;", html)


class BlocksTest(unittest.TestCase):
    def test_blockquote(self):
        html = md.render("> quoted **text**")
        self.assertEqual(html, "<blockquote>\n<p>quoted "
                               "<strong>text</strong></p>\n</blockquote>")

    def test_multiline_blockquote(self):
        html = md.render("> one\n> two")
        self.assertIn("one\ntwo", html)

    def test_hr(self):
        self.assertEqual(md.render("---"), "<hr>")
        self.assertEqual(md.render("a\n\n***\n\nb"),
                         "<p>a</p>\n<hr>\n<p>b</p>")


class RealDocumentsTest(unittest.TestCase):
    def test_all_documents_well_formed(self):
        for name in DOCS:
            with self.subTest(doc=name):
                checker = check_well_formed(md.render(read_doc(name)))
                self.assertEqual(checker.errors, [])
                self.assertEqual(checker.stack, [])

    def test_all_link_hrefs_non_empty(self):
        linked = {"README.md", "SOURCES.md", "NOTICE.md"}
        for name in DOCS:
            with self.subTest(doc=name):
                checker = check_well_formed(md.render(read_doc(name)))
                if name in linked:
                    self.assertTrue(checker.hrefs,
                                    "no links found in %s" % name)
                for href in checker.hrefs:
                    self.assertTrue(href, "empty href in %s" % name)

    def test_no_comments_survive(self):
        for name in DOCS:
            with self.subTest(doc=name):
                self.assertNotIn("<!--", md.render(read_doc(name)))

    def test_no_inline_styles(self):
        for name in DOCS:
            with self.subTest(doc=name):
                self.assertNotIn("style=", md.render(read_doc(name)))

    def test_readme_table_row_counts(self):
        counter = TableCounter()
        counter.feed(md.render(read_doc("README.md")))
        counter.close()
        self.assertEqual(counter.counts, [146, 77])

    def test_readme_num_class_present(self):
        self.assertIn('class="num"', md.render(read_doc("README.md")))

    def test_readme_headings(self):
        top = md.headings(read_doc("README.md"))[0]
        self.assertEqual(top, (1, "Long Hikes", "long-hikes"))

    def test_readme_offset(self):
        html = md.render(read_doc("README.md"), heading_offset=1)
        self.assertNotIn("<h1", html)
        self.assertIn('<h2 id="long-hikes">Long Hikes</h2>', html)

    def test_rewrite_called_for_every_real_link(self):
        seen = []
        html = md.render(read_doc("README.md"),
                         link_rewrite=lambda h: seen.append(h) or h)
        self.assertTrue(seen)
        for href in seen:
            self.assertTrue(href)

    def test_rewrite_changes_real_hrefs(self):
        plain = md.render(read_doc("SOURCES.md"))
        rewritten = md.render(read_doc("SOURCES.md"),
                              link_rewrite=lambda h: "/go/?u=" + h)
        self.assertNotEqual(plain, rewritten)
        self.assertNotIn('href="https://', rewritten)
        checker = check_well_formed(rewritten)
        self.assertEqual(checker.errors, [])
        self.assertEqual(checker.stack, [])


if __name__ == "__main__":
    unittest.main()
