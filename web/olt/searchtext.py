"""The words a search box looks in (data-search on each row of a list; app.js matches against them).

A row's words come in four tiers, strongest first, so that the list can put the best matches first:

    0  name        the name, its common name, its abbreviation and its id
    1  author      who made a route
    2  places      the full names of the states and provinces it lies in, the countries, the place it
                   starts and the place it ends, and the land unit or managing body its record names
    3  summary     the trail's summary

Each tier is folded (fold) and written once per word (the summary's words of fewer than three letters are
left out): a word that a stronger tier has is left out of the
weaker ones, since a search asks for the strongest tier a word is found in. The tiers are joined with "|".
app.js folds what is typed the same way (its fold(), checked against this one by web/tests/test_search.py)
and finds each typed word at the start of a word of the row.
"""
import re
import unicodedata

from . import common, facets, hike, words

TIERS = 4
SUMMARY = 3             # the summary tier
SUMMARY_MIN = 3         # it holds words of this many letters or more, and a typed word is looked for there only if it has as many
# A designation that only says who made the route, and that no agency holds it: the author is in
# the author tier already, and "no agency or association" would match every route.
_NO_BODY = re.compile(r"^(person-defined route|guidebook route)\b", re.I)
_APOSTROPHES = re.compile("[’‘'`´]")
_NOT_WORD = re.compile(r"[\W_]+")


def fold(text):
    """Lower-case, without accents, apostrophes dropped ("Road's End" -> "roads end"), every other run of
    anything that is not a letter or a digit a single space."""
    text = unicodedata.normalize("NFD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return _NOT_WORD.sub(" ", _APOSTROPHES.sub("", text)).strip()


def place_names(rec):
    """The names of the places a record carries: states, provinces and countries in full, where it
    starts and ends, and the land unit or body of its designation."""
    names = [facets.place_name(k) for k in facets.place_keys(rec)]
    names += [words.COUNTRIES.get(c, c) for c in common.countries(rec)]
    h = hike.table(rec)
    names += [h.get("start", ""), h.get("end", "")]
    designation = rec.get("designation", "")
    if designation and not _NO_BODY.match(designation):
        names.append(designation)
    return [n for n in names if isinstance(n, str) and n.strip()]


def tier_texts(rec):
    """The four texts of a record, unfolded."""
    return [
        " ".join([rec["name"], rec.get("common_name", ""), rec.get("short_name", ""), rec["id"]]),
        facets.author(rec),
        " ".join(place_names(rec)),
        hike.table(rec).get("summary", ""),
    ]


def tiers(rec):
    """The four tiers as lists of words, each word in the strongest tier that has it."""
    seen = set()
    out = []
    for i, text in enumerate(tier_texts(rec)):
        mine = []
        for word in fold(text).split():
            if i == SUMMARY and len(word) < SUMMARY_MIN:
                continue
            if word not in seen:
                seen.add(word)
                mine.append(word)
        out.append(mine)
    return out


def attribute(rec):
    """The value of a row's data-search: the tiers' words, tiers joined with "|"."""
    return "|".join(" ".join(t) for t in tiers(rec))
