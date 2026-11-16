"""Site-wide settings from web/site.toml (name, tagline, home_title, base_url, repo_url, repo_branch, contact_url, name_lang)."""
import functools
import os
import tomllib
import urllib.parse

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_TOML = os.path.join(WEB_DIR, "site.toml")


class Site:
    """The settings every page needs. Build one with load()."""

    def __init__(self, name, tagline, base_url="", repo_url="", repo_branch="main",
                 contact_url="", name_lang=None, home_title="", maintainer_name="", maintainer_url=""):
        if not name:
            raise ValueError("site.toml: name must not be empty")
        self.name = name
        self.tagline = tagline
        # The home page's own title, before the name is added (about 50 characters).
        self.home_title = home_title.strip()
        self.base_url = base_url.rstrip("/")
        self.repo_url = repo_url.rstrip("/")
        self.repo_branch = (repo_branch or "main").strip() or "main"
        self.contact_url = contact_url.strip()
        # Who maintains the site, and the page about them: shown on the About page and
        # named in the structured data. Both are public by the owner's choice.
        self.maintainer_name = maintainer_name.strip()
        self.maintainer_url = maintainer_url.strip()
        # record id -> language tag of its name ("fr"), for names that are not English
        self.name_lang = dict(name_lang or {})

    def canonical(self, path):
        """Absolute URL of a site path ("/trails/arizona/"), or "" when base_url is unset."""
        return self.base_url + path if self.base_url else ""

    @property
    def issues_url(self):
        """Where to report an error, or "" when repo_url is unset."""
        return self.repo_url + "/issues" if self.repo_url else ""

    @property
    def issue_chooser_url(self):
        """The repository's issue chooser (its forms and a blank issue), or "" when repo_url
        is not a GitHub repository."""
        return self.repo_url + "/issues/new/choose" if self.repo_url and self.is_github else ""

    @property
    def contact(self):
        """Where to write to the maintainers: contact_url, else the issue chooser, else "".
        No email address is ever built here; a mailto: contact_url is the owner's own choice."""
        return self.contact_url or self.issue_chooser_url

    @property
    def is_github(self):
        """True when repo_url is a github.com repository (the only host whose
        edit/history/issue-form URL shapes the site builds)."""
        return (urllib.parse.urlsplit(self.repo_url).hostname or "").lower() == "github.com"

    def _github_issue_form_url(self, template, params=()):
        query = urllib.parse.urlencode([("template", template), *params])
        return f"{self.repo_url}/issues/new?{query}"

    def correction_url(self, trail_id="", name=""):
        """Report-a-problem URL: the GitHub correction form prefilled with the
        trail (fields are prefilled by their form id), else the issues list,
        else "" when repo_url is unset."""
        if not self.repo_url:
            return ""
        if not self.is_github:
            return self.issues_url
        params = []
        if trail_id:
            title = f"Correction: {name} ({trail_id})" if name else f"Correction: {trail_id}"
            params = [("title", title), ("trail", trail_id)]
        return self._github_issue_form_url("correction.yml", params)

    @property
    def new_trail_url(self):
        """Suggest-a-trail URL: the GitHub new-trail form, else the issues list, else ""."""
        if not self.repo_url:
            return ""
        if not self.is_github:
            return self.issues_url
        return self._github_issue_form_url("new-trail.yml")

    @property
    def removal_url(self):
        """Track/logo removal URL: the GitHub removal form, else the issues list, else ""."""
        if not self.repo_url:
            return ""
        if not self.is_github:
            return self.issues_url
        return self._github_issue_form_url("removal.yml")

    def edit_url(self, trail_id):
        """GitHub edit URL for <id>/trail.toml, or "" for any other host / no repo."""
        if not self.is_github:
            return ""
        branch = urllib.parse.quote(self.repo_branch, safe="/")
        return f"{self.repo_url}/edit/{branch}/{urllib.parse.quote(trail_id, safe='')}/trail.toml"

    def history_url(self, trail_id):
        """GitHub commit-history URL for <id>/, or "" for any other host / no repo."""
        if not self.is_github:
            return ""
        branch = urllib.parse.quote(self.repo_branch, safe="/")
        return f"{self.repo_url}/commits/{branch}/{urllib.parse.quote(trail_id, safe='')}"

    def blob_url(self, path):
        """Repository URL of a file at repo_branch, or "" when repo_url is unset."""
        if not self.repo_url:
            return ""
        branch = urllib.parse.quote(self.repo_branch, safe="/")
        return f"{self.repo_url}/blob/{branch}/{path.lstrip('/')}"


def from_file(path):
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return Site(name=data.get("name", ""), tagline=data.get("tagline", ""),
                base_url=data.get("base_url", ""), repo_url=data.get("repo_url", ""),
                repo_branch=data.get("repo_branch", "main"),
                contact_url=data.get("contact_url", ""), name_lang=data.get("name_lang", {}),
                home_title=data.get("home_title", ""),
                maintainer_name=data.get("maintainer_name", ""), maintainer_url=data.get("maintainer_url", ""))


@functools.cache
def load():
    """The settings in web/site.toml (read once per process)."""
    return from_file(SITE_TOML)
