"""Tests for who the site says maintains it, when each trail was last checked, and the generated
"In brief" paragraph at the top of every trail page.

Records come from the repository, so the paragraph is checked against what a record really holds;
a sparse record is built here. The site is not built: pages are rendered one record at a time.
"""
import copy
import html
import json
import os
import re
import sys
import unittest

WEB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB)
sys.path.insert(0, WEB)

from olt import common, docs, hike, records, seo, site, trail  # noqa: E402

SITE = site.load()


def load(tid):
    rec = records.load_record(ROOT, tid)
    if tid in SITE.name_lang:
        rec["derived"]["name_lang"] = SITE.name_lang[tid]
    return rec


def text_of(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", str(fragment)))


def sparse_record():
    """A record with no [hike] table: a name, a length, a place and a source."""
    return {
        "id": "sparse", "name": "Sparse Trail", "country": "US", "regions": ["AZ"], "length_km": 100,
        "length_note": "", "tier": "regional", "designation": "A & B Association", "wave": 1,
        "source": {"status": "none", "publisher": "P", "url": "https://example.org/", "format": "None",
                   "crs": "EPSG:4326", "licence": "none-stated", "licence_text": "None.", "attribution": "none",
                   "osm_only": False, "mainline": "None", "source_checked": "2026-11-10", "redistributable": True,
                   "line_source": "none (no line included)", "line_file": "", "line_absent_reason": "None."},
        "osm": {"relation": 0, "note": "None"},
        "shield": {"status": "no-logo-exists", "logo_source": "", "contact": "P", "note": "None",
                   "logo_file": "", "logo_owner": "P"},
        "verification": {"verified": False, "note": "No line to measure."},
        "derived": {"kind": "designated", "has_line": False, "length_mi": 62, "files": {},
                    "status": "record-only", "downloads": []},
    }


class MaintainerSettings(unittest.TestCase):
    def test_site_toml_names_the_maintainer_and_nothing_personal(self):
        self.assertEqual(SITE.maintainer_name, "Stephen Waits")
        self.assertEqual(SITE.maintainer_url, "https://github.com/swaits")
        with open(site.SITE_TOML, encoding="utf-8") as f:
            text = f.read()
        self.assertNotIn("@", re.sub(r"#.*", "", text), "no email address in the settings")

    def test_contact_is_the_issue_chooser(self):
        self.assertEqual(SITE.issue_chooser_url, SITE.repo_url + "/issues/new/choose")
        self.assertEqual(SITE.contact, SITE.issue_chooser_url)
        owner = site.Site("N", "T", repo_url="https://github.com/o/r", contact_url="https://example.org/contact")
        self.assertEqual(owner.contact, "https://example.org/contact")
        elsewhere = site.Site("N", "T", repo_url="https://git.example.org/o/r")
        self.assertEqual(elsewhere.issue_chooser_url, "")
        self.assertEqual(elsewhere.contact, "")

    def test_about_section_comes_from_the_settings(self):
        body = str(docs.about_page([load("appalachian")], SITE, ROOT)[2])
        self.assertIn('<h2 id="who-maintains">Who maintains this</h2>', body)
        self.assertIn(f'<a href="{SITE.maintainer_url}">{SITE.maintainer_name}</a>', body)
        self.assertIn(f'<a href="{SITE.issue_chooser_url}">open an issue on GitHub</a>', body)
        section = body[body.index('id="who-maintains"'):]
        section = section[:section.index("</section>")]
        for claim in ("public domain", "names the page it was read on", "no ads, no accounts, no tracking and no analytics"):
            self.assertIn(claim, section)
        self.assertNotRegex(section, r"[\w.]+@[\w.]+", "no email address")

    def test_no_maintainer_no_section_and_no_person(self):
        bare = site.Site("N", "T", base_url="https://example.org", repo_url="https://github.com/o/r")
        self.assertEqual(docs.maintainer_section(bare), "")
        self.assertEqual(seo.person_node(bare), {})
        self.assertNotIn("founder", seo.organization_node(bare))

    def test_structured_data_names_the_maintainer_by_profile(self):
        person = seo.person_node(SITE)
        self.assertEqual(person["@type"], "Person")
        self.assertEqual(person["name"], SITE.maintainer_name)
        self.assertEqual(person["sameAs"], [SITE.maintainer_url])
        self.assertNotIn("email", json.dumps(person))
        org = next(n for n in seo.home_jsonld(SITE) if n["@type"] == "Organization")
        self.assertEqual(org["founder"], person)
        self.assertEqual(org["contactPoint"]["url"], SITE.issue_chooser_url)
        data = seo.dataset_jsonld([load("appalachian")], SITE, version="2026-11-16")
        self.assertEqual(data["creator"], person)
        self.assertEqual(data["maintainer"], person)
        self.assertEqual(data["publisher"]["@type"], "Organization")
        self.assertNotRegex(json.dumps([org, data]), r"[\w.+-]+@[\w-]+\.[\w.]+", "no email address")


class LastChecked(unittest.TestCase):
    def test_shown_date_is_the_records_newest_check_and_equals_date_modified(self):
        for tid in ("appalachian", "timberline", "circle-of-solitude"):
            rec = load(tid)
            body = str(trail.render(rec, SITE, [rec])[2])
            shown = re.search(r'Last checked <time datetime="(\d{4}-\d{2}-\d{2})">(\d{4}-\d{2}-\d{2})</time>', body)
            self.assertTrue(shown, tid)
            self.assertEqual(shown.group(1), shown.group(2))
            checks = [rec.get("verification", {}).get("date"), hike.table(rec).get("checked"),
                      rec["source"].get("source_checked")]
            self.assertEqual(shown.group(1), max(str(c) for c in checks if c))
            page = seo.trail_jsonld(rec, SITE, title="t", description="d")[0]
            self.assertEqual(page["dateModified"], shown.group(1))

    def test_a_history_entry_is_not_a_check(self):
        rec = load("appalachian")
        rec["history"] = [{"date": "2099-01-01", "change": "x", "fields": [], "asked_by": "x"}]
        self.assertNotEqual(seo.checked(rec), "2099-01-01")
        self.assertEqual(seo.modified(rec), "2099-01-01")

    def test_no_date_no_line(self):
        rec = sparse_record()
        del rec["source"]["source_checked"]
        self.assertEqual(seo.checked(rec), "")
        self.assertEqual(str(trail.checked_line(rec)), "")


class InBrief(unittest.TestCase):
    def sentences(self, rec):
        return [text_of(s) for s in trail.brief_sentences(rec)]

    def test_full_record(self):
        rec = load("appalachian")
        s = self.sentences(rec)
        self.assertEqual(s[0], "The Appalachian Trail is a 2,198-mile (3,537 km) National Scenic Trail, designated in 1968, "
                               "through forest and alpine country across 14 states of the United States.")
        self.assertEqual(s[1], "It runs from Springer Mountain, Georgia, to Katahdin, Maine, and walking all of it "
                               "usually takes 5 to 7 months.")
        self.assertEqual(s[2], "Its highest point is Kuwohi (Clingmans Dome), at 6,624 ft (2,019 m), and the track climbs "
                               "466,594 ft (142,218 m) in total, computed from the track.")
        self.assertEqual(s[3], "Northbound hikes start late February to early April, and this page has a GPX "
                               "of the track to download.")
        self.assertEqual(len(s), 4)

    def test_season_is_said_as_a_sentence_that_fits_the_field(self):
        def season(text):
            rec = sparse_record()
            rec["hike"] = {"season": text}
            return trail.season_sentence(rec)
        self.assertEqual(season("May to July"), ("range", "The usual season is May to July"))
        self.assertEqual(season("Spring and fall"), ("range", "The usual season is spring and fall"))
        self.assertEqual(season("Late July through September"), ("range", "The usual season is late July through September"))
        self.assertEqual(season("All year"), ("sentence", "It can be walked all year"))
        self.assertEqual(season("Northbound hikes start late February to early April"),
                         ("sentence", "Northbound hikes start late February to early April"))
        # a range with a note after it keeps the range; a long note with nothing to cut at is left to "At a glance"
        self.assertEqual(season("Spring and fall; summers tend to be humid and buggy"),
                         ("range", "The usual season is spring and fall"))
        self.assertIsNone(season("Best travelled " + "in the later part of the summer " * 5))

    def test_a_permit_is_said_only_when_it_is_short(self):
        short = sparse_record()
        short["hike"] = {"permit": "No permit is needed to hike it."}
        self.assertEqual(trail.permit_sentence(short), "No permit is needed to hike it.")
        long = sparse_record()
        long["hike"] = {"permit": "Some sections need a permit: East Bay lands need a trail permit, and another section needs a docent."}
        self.assertEqual(trail.permit_sentence(long), "")

    def test_sparse_record_says_only_what_it_holds(self):
        s = self.sentences(sparse_record())
        self.assertEqual(s, ["The Sparse Trail is a 62-mile (100 km) trail in Arizona, United States.",
                             "This site has no GPX for it."])

    def test_route_names_a_plain_author_and_leaves_out_a_nickname(self):
        plain = load("bigfoot-trail")
        self.assertIn("a 360-mile (579 km) route by Michael Kauffmann, dating from 2009, through forest country",
                      self.sentences(plain)[0])
        nick = load("great-basin-trail")
        self.assertIn('Ryan "Dirtmonger" Sylva', nick["route"]["creator"])
        self.assertNotIn("Dirtmonger", " ".join(self.sentences(nick)))
        self.assertRegex(self.sentences(nick)[0], r"-mile \([\d,]+ km\) loop route through ")

    def test_loop_network_and_partial_track(self):
        loop = self.sentences(load("timberline"))
        self.assertIn("loop trail", loop[0])
        self.assertTrue(any(x.startswith("It starts and ends at Timberline Lodge") for x in loop))
        net = self.sentences(load("finger-lakes"))
        self.assertIn("trail network", net[0])
        self.assertTrue(any(x.startswith("Most walks start at ") for x in net))
        part = self.sentences(load("allegheny-trail"))
        self.assertTrue(any("computed from the part of the track on file, about 6% of the published length" in x for x in part))
        self.assertTrue(any(x == "This page has a GPX of part of the track to download." for x in part))

    def test_trail_without_a_track_and_french_name(self):
        free = self.sentences(load("circle-of-solitude"))
        self.assertTrue(any("this site has no GPX for it" in x.lower() for x in free))
        fr = load("traversee-charlevoix")
        self.assertTrue(self.sentences(fr)[0].startswith("Traversée de Charlevoix is a "))
        self.assertIn('<span lang="fr">', str(trail.brief_sentences(fr)[0]))

    def test_a_place_name_that_starts_with_near_reads_mid_sentence(self):
        s = self.sentences(load("lone-star"))
        self.assertIn("It runs from near Richards, Texas, to near Cleveland, Texas.", " ".join(s))
        for rec in records.load_records(ROOT):
            self.assertNotRegex(" ".join(self.sentences(rec)), r"\b(from|to|at) Near ", rec["id"])

    def test_article_follows_the_spoken_number(self):
        self.assertIn(" is an 81-mile ", self.sentences(load("avon"))[0])
        self.assertIn(" is an 800-mile ", self.sentences(load("desert-winter-thru-hike"))[0])

    def test_every_record_gets_a_paragraph_the_record_can_support(self):
        for rec in records.load_records(ROOT):
            if rec["id"] in SITE.name_lang:
                rec["derived"]["name_lang"] = SITE.name_lang[rec["id"]]
            s = self.sentences(rec)
            paragraph = " ".join(s)
            self.assertGreaterEqual(len(s), 2, rec["id"])
            self.assertLessEqual(len(s), 4, rec["id"])
            self.assertIn("GPX", paragraph, rec["id"])
            self.assertNotRegex(paragraph, r"\b(Season|Permits are noted)\b", rec["id"])
            for bad in ("None", "{", "}", "  ", " ,", " .", "unknown", "not known", "n/a"):
                self.assertNotIn(bad, paragraph, rec["id"])
            self.assertIn(f"{rec['derived']['length_mi']:,}-mile", paragraph, rec["id"])
            self.assertIn(f"({words_km(rec)} km)", paragraph, rec["id"])
            summary = hike.summary(rec)
            for sentence in re.split(r"(?<=[.!?])\s+", summary):
                self.assertNotIn(sentence.strip(), s, f"{rec['id']} repeats its summary word for word")
            h = hike.table(rec)
            if h.get("days"):
                self.assertIn("usually takes", paragraph, rec["id"])
            else:
                self.assertNotIn("usually takes", paragraph, rec["id"])
            if not (h.get("season") or h.get("months")):
                self.assertNotRegex(paragraph, r"usual season|walked all year|Northbound|season", rec["id"])
            if "No permit" in paragraph or "permit" in paragraph.lower():
                self.assertIn(common.sentence(h.get("permit", "")), paragraph, rec["id"])
            self.assertEqual("highest point" in paragraph,
                             bool(h.get("high_point") or h.get("high_point_m") or rec["derived"].get("elevation")), rec["id"])

    def test_the_map_area_comes_first_and_the_paragraph_is_under_it(self):
        rec = load("appalachian")
        body = str(trail.render(rec, SITE, [rec])[2])
        order = ['class="titleblock', 'class="trail-actions"', 'class="mapfig ', 'id="glance-title"',
                 'class="detail__text"', 'id="brief-title"', 'class="trail-summary"', 'class="trail-brief"',
                 'class="note trail-checked"']
        at = [body.index(x) for x in order]
        self.assertEqual(at, sorted(at), order)
        self.assertIn('<h2 id="brief-title" class="vh">In brief</h2>', body)
        self.assertIn("<strong>In brief.</strong>", body)
        self.assertLess(body.index('id="brief-title"'), body.index('id="morelinks-title"') if 'id="morelinks-title"' in body else len(body))

    def test_nothing_stands_between_the_head_and_the_map(self):
        rec = load("appalachian")
        body = str(trail.render(rec, SITE, [rec])[2])
        between = body[body.index('class="page-head page-head--trail"'):body.index('class="mapfig ')]
        self.assertNotIn("trail-lede", between)
        self.assertNotIn("trail-summary", between)
        # the actions are part of the head, and the phone's strip of key facts is the only thing after it
        head = between[:between.index('<div class="container detail')]
        self.assertIn('class="trail-actions"', head)
        self.assertIn('class="trail-strip"', between[len(head):])


def words_km(rec):
    from olt import words
    return words.fmt_km(rec["length_km"])


if __name__ == "__main__":
    unittest.main()
