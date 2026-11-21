"""The Google tag: on every built page exactly once, only when site.toml sets it, and allowed by the CSP."""
import base64
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WEB)

from olt import layout, pages, site  # noqa: E402

TAG_ID = "GTM-TEST1234"
LOADER = f'<script async src="https://www.googletagmanager.com/gtm.js?id={TAG_ID}"></script>'


def html_files(root):
    for base, _, names in os.walk(root):
        for n in names:
            if n.endswith(".html"):
                yield os.path.join(base, n)


def start_build(out, tag):
    """Start a build of the site into out with this tag in site.toml (none when tag is empty)."""
    cfg = os.path.join(os.path.dirname(out), "site.toml")
    with open(os.path.join(WEB, "site.toml"), encoding="utf-8") as f:
        text = re.sub(r'(?m)^google_tag = .*\n', "", f.read())
    with open(cfg, "w", encoding="utf-8") as f:
        f.write((f'google_tag = "{tag}"\n' if tag else "") + text)
    code = ("import sys; sys.path.insert(0, %r); from olt import site; "
            "site.SITE_TOML = %r; site.load.cache_clear(); import build; build.main(['--out', %r])"
            % (WEB, cfg, out))
    return subprocess.Popen([sys.executable, "-c", code], cwd=WEB,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class GoogleTagTest(unittest.TestCase):
    def test_every_built_page_has_the_tag_once_and_none_without_the_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            on, off = os.path.join(tmp, "on", "site"), os.path.join(tmp, "off", "site")
            started = []
            for out, tag in ((on, TAG_ID), (off, "")):
                os.makedirs(os.path.dirname(out))
                started.append(start_build(out, tag))  # both at once: they share nothing
            for proc in started:
                self.assertEqual(proc.wait(), 0)
            pages_on = list(html_files(on))
            self.assertGreater(len(pages_on), 200)
            for name in ("404.html", os.path.join("saved", "index.html"), "index.html"):
                self.assertTrue(os.path.isfile(os.path.join(on, name)), name)
            for path in pages_on:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                head = text[:text.index("</head>")]
                self.assertEqual(text.count("googletagmanager.com"), 1, path)
                self.assertEqual(text.count(LOADER), 1, path)
                self.assertEqual(text.count("gtag('js', new Date());"), 1, path)
                self.assertIn(LOADER, head, path)
            for path in html_files(off):
                with open(path, encoding="utf-8") as f:
                    text = f.read()
                self.assertNotIn("googletagmanager", text, path)
                self.assertNotIn("gtag", text, path)

    def test_the_real_setting_is_the_owners_container(self):
        self.assertEqual(site.load().google_tag, "GTM-WWLZSH6Q")

    def test_the_policy_allows_the_tag_and_its_inline_script_by_hash(self):
        digest = base64.b64encode(hashlib.sha256(layout.GOOGLE_TAG_INLINE.encode()).digest()).decode()
        with open(os.path.join(WEB, "static", "_headers"), encoding="utf-8") as f:
            policy = next(l for l in f if "Content-Security-Policy:" in l)
        script_src = re.search(r"script-src ([^;]*);", policy).group(1)
        self.assertIn("https://www.googletagmanager.com", script_src)
        self.assertIn(f"'sha256-{digest}'", script_src)
        self.assertNotIn("unsafe-inline", script_src)


if __name__ == "__main__":
    unittest.main()
