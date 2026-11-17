"""Two pages built from how the records point at each other and at their own history:

    /recent/      the newest additions, and the newest changes, from each record's [[history]]
    /connected/   trails whose own words name another trail, grouped under the trail they name

Nothing names a trail. "Newest" is measured from the newest date the records give, never from the
day the site is built, so a page does not change until the data does.
"""
import collections

from . import browse, common, facets, home, pagekit, related, seo
from .markup import Markup, esc

RECENT = "/recent/"
CONNECTED = "/connected/"
ADDED_MIN = 20          # whole days of additions are shown until at least this many trails are
CHANGE_ROWS = 30
GROUP_MIN = 3           # a trail is a group when at least this many others name it


# Recent -----------------------------------------------------------------------------

def added_date(rec):
    """The date of the entry that added the record."""
    for e in rec.get("history", []):
        if isinstance(e, dict) and e.get("fields") == ["record"]:
            return str(e.get("date", ""))
    return ""


def recent_added(records):
    """[(date, [trails])], newest day first, whole days until at least ADDED_MIN trails."""
    days = collections.defaultdict(list)
    for r in records:
        d = added_date(r)
        if d:
            days[d].append(r)
    out, count = [], 0
    for d in sorted(days, reverse=True):
        out.append((d, sorted(days[d], key=lambda r: r["id"])))
        count += len(days[d])
        if count >= ADDED_MIN:
            break
    return out


def recent_changes(records):
    """(rows, total): the newest applied changes to a record's facts, as (date, trail, what), newest first
    and in name order within a day; and how many such changes there are."""
    found = []
    for r in records:
        for e in r.get("history", []):
            if (isinstance(e, dict) and e.get("outcome") == "applied" and e.get("fields") != ["record"]
                    and e.get("date")):
                found.append((str(e["date"]), r, e.get("change", "")))
    found.sort(key=lambda t: (t[0], ), reverse=True)
    found.sort(key=lambda t: (-int(t[0].replace("-", "")), t[1]["name"].lower()))
    return found[:CHANGE_ROWS], len(found)


def recent_page(records, site):
    """(title, description, body, recs) for /recent/, or None when fewer than MIN_SIZE trails were added."""
    added = recent_added(records)
    recs = [r for _, rs in added for r in rs]
    if len(recs) < browse.MIN_SIZE:
        return None
    changes, total = recent_changes(records)
    newest = seo.newest(records)
    groups = [(f"Added {d} ({len(rs)})", rs, None) for d, rs in added]
    items = [pagekit.plain_entry(pagekit.trail_link(r), heading=False, text=[esc(change)],
                                 small=[f'<time datetime="{esc(d)}">{esc(d)}</time>']) for d, r, change in changes]
    lede = (f"The {len(recs)} newest additions, from each trail&rsquo;s own history, and the newest of the {total} changes "
            f"made to a trail&rsquo;s facts. The newest date in the data is {esc(newest)}.")
    body = (pagekit.head("Recently added and changed", lede, [("Trails", "/"), ("Lists", "/lists/")])
            + f"""<div class="container section place">
  <h2 class="vh">Newly added trails</h2>
  {home.browse_view(home.results(groups=groups, top=3), home.overview_map(recs, "Map of the newest trails"),
                    about=f"""{pagekit.plain_list(items, "The newest changes")}
  <p class="finder__foot">Each trail keeps its own history, shown at the foot of its page. The
  <a href="/data/changelog/">changelog</a> lists changes to the site and the dataset as a whole.</p>""", about_title="Newest changes", about_id="newest-changes")}
</div>""")
    title = "Recently Added Long Hiking Trails and Changes"
    desc = common.cut_at_word(f"The {len(recs)} newest long hiking trails and the newest changes to them, "
                              f"from each trail's history. Newest date: {newest}.", common.DESCRIPTION_LIMIT)
    return title, desc, Markup(body), recs


# Connected ------------------------------------------------------------------------------

def connections(records):
    """[(trail named, [trails that name it])] for every trail that at least GROUP_MIN other trails'
    own descriptions name, most named first. Only the description names it: no sharing of a name counts."""
    graph = related._once(records, "related", lambda: related._related_graph(records))
    by_id = {r["id"]: r for r in records}
    out = []
    for rid, edges in graph.items():
        namers = [by_id[o] for o, why in edges.items() if why == "names"]
        if len(namers) >= GROUP_MIN:
            out.append((by_id[rid], sorted(namers, key=lambda r: r["id"])))
    out.sort(key=lambda t: (-len(t[1]), t[0]["id"]))
    return out


def connected_page(records, site):
    """(title, description, body, recs) for /connected/, or None when fewer than MIN_SIZE trails are in groups.

    A trail is listed once, under the first group it belongs to (the one named by most others), so the
    rows are the trails."""
    groups = connections(records)
    seen = set()
    sections = []
    recs = []
    for named, namers in groups:
        fresh = [r for r in namers if r["id"] not in seen]
        seen.update(r["id"] for r in fresh)
        if fresh:
            sections.append((f'Trails that name <a href="{esc(common.trail_path(named))}">{common.name(named)}</a> '
                             f'({len(fresh)})', fresh, None))
            recs += fresh
    if len(recs) < browse.MIN_SIZE:
        return None
    lede = (f"{len(groups)} trails that other trails&rsquo; own descriptions name. Under each one are the trails whose "
            f"own description names it, {len(recs)} trails in all, each listed once. A description names another trail when its summary, "
            f"designation, caution or route note uses that trail&rsquo;s name. It does not say the two meet.")
    body = (pagekit.head("Linked long trails", lede, [("Trails", "/"), ("Lists", "/lists/")])
            + f"""<div class="container section place">
  {home.results(groups=sections, top=2)}
</div>""")
    title = "Linked Long Trails: Trails That Name Other Trails"
    desc = common.cut_at_word(f"{len(groups)} long trails that other trails name in their own descriptions, with the "
                              f"{len(recs)} trails that name them.", common.DESCRIPTION_LIMIT)
    return title, desc, Markup(body), recs
