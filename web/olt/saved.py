"""The Saved page, /saved/: the visitor's saved trails, or a list opened from a link.

Saved trails are kept in the visitor's browser only: localStorage, key
lh-saved, the trail ids in the order saved (app.js). A link carries a list in
its own address, /saved/?t=<id>,<id>,..., so it opens the same list on any
device, in any browser, with nothing remembered.

The page is written like every other, so it cannot know the list. It holds
every trail's row, hidden (the same rows as the catalogue, about as heavy as
the home page's list; the hidden rows' logos are not fetched), and app.js
(initSavedPage) shows the right ones:

    own list       no t= in the address: the visitor's saved trails, the map
                   of them, and the link to them with a Copy link button
    nothing saved  no t=, nothing saved: how to save a trail, and a link to the trails
    from a link    t= in the address: that list, marked as from a link, with
                   "Save these" (adds it to the visitor's own) and a way to
                   their own list; ids that match no trail are dropped and
                   counted. A link holding the visitor's own list is shown as theirs.

Without JavaScript the page says that saved trails need it. It is not
indexed (layout noindex) and not in the sitemap (seo.all_paths).
"""
from . import common, home
from .markup import Markup

PATH = "/saved/"
TITLE = "Saved trails"
DESCRIPTION = "The trails you saved, kept in this browser, and a link that opens the same list anywhere."


def saved_page(records, site):
    """(title, description, body) for /saved/."""
    recs = sorted(records, key=home.sort_name)
    star = common.ICON_STAR
    body = f"""<div class="page-head saved-head" data-saved-page>
  <div class="container">
    <header class="titleblock"><div class="titleblock__text">
      <h1 data-saved-title>{TITLE}</h1>
      <p class="page-head__lede" data-saved-lede>Trails you save are kept here, in this browser on this device.</p>
    </div></header>
    <div class="notice saved-nojs"><p>Saved trails need JavaScript, which is off or blocked in this browser. <a href="/">See every trail</a>.</p></div>
    <div class="notice saved-from" data-saved-from hidden>
      <p><strong>This list came from a link.</strong> Opening it has not changed your own saved trails.</p>
      <p data-saved-dropped hidden></p>
      <p class="cluster">
        <button class="button button--primary" type="button" data-saved-merge>{star}Save these</button>
        <a class="button button--quiet" href="{PATH}">Your saved trails</a>
      </p>
      <p class="saved-status" data-saved-merged role="status"></p>
    </div>
    <section class="share" data-saved-share hidden aria-labelledby="share-title">
      <h2 class="share__title" id="share-title">Link to this list</h2>
      <p class="share__what">Bookmark it, or send it to another device or another person: it opens this same list in any browser.</p>
      <div class="share__row">
        <code class="share__url" id="saved-url" data-saved-url></code>
        <button class="button button--quiet" type="button" data-copy="#saved-url" data-copy-status="#saved-copied" data-copy-done="Link copied." hidden>Copy link</button>
      </div>
      <p class="share__done" id="saved-copied" role="status"></p>
    </section>
  </div>
</div>
<div class="container section saved-body">
  <div class="empty-state saved-empty" data-saved-empty hidden>
    <p><strong>Nothing saved yet.</strong></p>
    <p>To save a trail, select the {star}<span class="vh">star</span> in its row in any list of trails, or Save on the trail&rsquo;s page.</p>
    <p><a class="button button--primary" href="/">Find a trail</a></p>
  </div>
  <div class="empty-state saved-empty" data-saved-none hidden>
    <p><strong>None of the trails in this link are on this site.</strong></p>
    <p><a href="/">See every trail</a>, or <a href="{PATH}">your saved trails</a>.</p>
  </div>
  <div class="saved-list" data-saved-list hidden>
    {home.overview_map(recs, "Map of the trails in this list", wide=True, scope="all", saved=True)}
    {home.results(recs, saved=True)}
  </div>
</div>"""
    return TITLE, DESCRIPTION, Markup(body)
