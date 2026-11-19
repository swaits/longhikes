"""The Considered and left out page (/left-out/): built from left-out.toml.

left-out.toml holds the trails and routes that were looked at and left out
of the dataset, with the reason, the deciding fact, the page that shows it
and the date the decision was made. Its fields are in docs/schema.md.
Everything on this page comes from that file and from web/site.toml.
"""
import os
import tomllib

from . import pagekit, words
from .markup import Markup, esc

FILE_NAME = "left-out.toml"
PATH = "/left-out/"
REAL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# reason -> (heading, one plain sentence on what the heading means).
# Ordered as the inclusion rule states them; the page follows this order.
REASONS = {
    "below-floor": ("Below the 50 mile floor",
                    "The floor for this list is 50 miles (80 km). A trail or route under 50 miles is listed only when it is still reasonably long and at least one of these is true: it has real cross-country travel; "
                    "it genuinely takes five or more days to walk, as its author or managing body gives the trip (a guidebook spreading an ordinary trail trip over five days does not count); "
                    "or it is very well known and popular, as the Rae Lakes Loop is. Being close to 50 miles is never a reason. "
                    "The floor is tested on the length with nothing counted twice, so an out-and-back is judged one way. "
                    "A trail with its own name and its own published length is listed even where it lies on a longer listed trail; a guidebook's cut of a longer trail is not. "
                    "A listed trail or route also needs a published length."),
    "rail-trail-or-towpath": ("Rail trails and canal towpaths",
                              "Paths made mainly for cycling, such as gravel rail trails and canal towpaths, are not listed."),
    "driving-route": ("Mainly driving or motor routes",
                      "Historic trails that are mainly driving routes with short walkable pieces are not listed."),
    "not-mainly-walking": ("Mainly for bikes, horses or motor vehicles",
                           "A trail made mainly for other users is not a walking trail for this list."),
    "network": ("Networks, not one trail",
                "This list holds one named trail or route at a time, not a whole network of trails."),
    "cannot-be-walked-through": ("Cannot be walked through",
                                 "A listed trail is one route from end to end. Road links count, and so does "
                                 "a ferry, shuttle or bus link its holder or author names as the way through."),
    "mostly-unbuilt": ("Mostly unbuilt or still proposed",
                       "A trail that does not yet exist on the ground cannot be listed."),
    "requires-climbing": ("Requires roped or technical climbing",
                          "Nothing harder than Class 3 may be required, apart from a few short Class 4 scrambles. A route that needs a rope, a belay or rock-climbing skill is not listed, unless that section is optional."),
    "not-published-as-route": ("Not published as a route by its author",
                               "A route is listed when its author has published it as a route, with a stated length."),
    "waiting": ("Waiting",
                "Not left out for good. Each entry says what would change the decision."),
}
REASON_ORDER = tuple(REASONS)


def load_entries(repo_root):
    """The [[trail]] entries of left-out.toml, or [] when the file is not there."""
    for base in (repo_root, REAL_ROOT):
        path = os.path.join(base, FILE_NAME)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                doc = tomllib.load(f)
            return doc.get("trail") or []
    return []


def _where(entry):
    names = [words.region_name(str(c)) for c in entry.get("regions", [])]
    return ", ".join(names)


def _length(entry):
    """The length as the holder or author states it: length_note in words,
    else both units with miles first, else nothing (no page states one)."""
    note = entry.get("length_note")
    if note:
        return esc(note)
    km = entry.get("length_km")
    mi = entry.get("length_mi")
    if km is None and mi is not None:
        km = mi * words.KM_PER_MI
    if km is None:
        return Markup("")
    return words.length(km, mi=mi)


def _opening(entries, site):
    n = len(entries)
    gone = sum(1 for e in entries if e.get("was_listed"))
    second = ("Every one of them is a good walk in its own right and was left "
              "out only because it does not meet the rule this list uses")
    if gone:
        second += (f", and {gone} of them {'were' if gone != 1 else 'was'} "
                   "listed here once and later removed")
    parts = [
        f"This page lists {n} trails and routes that were considered for this "
        "dataset and left out, with the reason, the deciding fact and the date "
        "for each one.",
        second + ".",
    ]
    ask = "open an issue"
    if site.issues_url:
        ask = f'<a href="{esc(site.issues_url)}">open an issue</a>'
    parts.append(
        f"If the facts behind a decision have changed, {ask} and give a page "
        "that shows the change, and the decision will be looked at again.")
    return Markup(" ".join(parts))


def left_out_page(entries, site, repo_root):
    """(title, description, body) for /left-out/, from left-out.toml entries."""
    bread = Markup('<nav class="breadcrumb" aria-label="Breadcrumb"><ol>'
                   '<li><a href="/about/">About</a></li>')
    groups = ""
    for reason in REASON_ORDER:
        listed = [e for e in entries if e.get("reason") == reason]
        if not listed:
            continue
        heading, meaning = REASONS[reason]
        items = []
        for e in listed:
            # In the language of a trail's row: the name as a row's name, "once listed here" as a tag
            # where a route's tag is, where and how long as its line of facts, the deciding sentence
            # as its text, the date and the source as small print.
            tag = '<span class="tag">Once listed here</span>' if e.get("was_listed") else ""
            text = [esc(e.get("note", ""))]
            if e.get("waiting_for"):
                text.append(f"It would be listed if this changes: {esc(e['waiting_for'])}")
            small = [f'Decided <time datetime="{esc(e.get("decided", ""))}">{esc(e.get("decided", ""))}</time>']
            if e.get("source_url"):
                small.append(f'<a href="{esc(e["source_url"])}">Source page</a>')
            items.append(pagekit.plain_entry(esc(e.get("name", "")), tag=tag, text=text,
                                             facts=[esc(_where(e)), _length(e)], small=small))
        groups += f"""<section class="left-out__group" aria-labelledby="left-out-{esc(reason)}">
  <div class="section-head"><h2 id="left-out-{esc(reason)}">{esc(heading)}</h2>
  <p>{esc(meaning)}</p></div>
  {pagekit.plain_list(items)}
</section>"""
    body = f"""<div class="page-head"><div class="container">{bread}<li aria-current="page">Considered and left out</li></ol></nav><header class="titleblock">
  <div class="titleblock__text"><h1>Considered and left out</h1>
  <p class="page-head__lede">Trails and routes that were looked at for this dataset and left out, and why.</p>
  </div></header></div></div>
<div class="container section place left-out">
  <p class="prose">{_opening(entries, site)}</p>
  {groups}
</div>"""
    description = (f"{len(entries)} trails and routes considered for {site.name} and left out: "
                   "the reason, the deciding fact and its source page for each one.")
    return "Trails Considered and Left Out, and Why", description, Markup(body)
