"""Site-wide settings from web/site.toml (name, tagline, base_url, repo_url, contact_url, name_lang)."""
import functools
import os
import tomllib

WEB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_TOML = os.path.join(WEB_DIR, "site.toml")


class Site:
    """The settings every page needs. Build one with load()."""

    def __init__(self, name, tagline, base_url="", repo_url="", contact_url="", name_lang=None):
        if not name:
            raise ValueError("site.toml: name must not be empty")
        self.name = name
        self.tagline = tagline
        self.base_url = base_url.rstrip("/")
        self.repo_url = repo_url.rstrip("/")
        self.contact_url = contact_url.strip()
        # record id -> language tag of its name ("fr"), for names that are not English
        self.name_lang = dict(name_lang or {})

    def canonical(self, path):
        """Absolute URL of a site path ("/trails/arizona/"), or "" when base_url is unset."""
        return self.base_url + path if self.base_url else ""

    @property
    def issues_url(self):
        """Where to report an error, or "" when repo_url is unset."""
        return self.repo_url + "/issues" if self.repo_url else ""


def from_file(path):
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return Site(name=data.get("name", ""), tagline=data.get("tagline", ""),
                base_url=data.get("base_url", ""), repo_url=data.get("repo_url", ""),
                contact_url=data.get("contact_url", ""), name_lang=data.get("name_lang", {}))


@functools.cache
def load():
    """The settings in web/site.toml (read once per process)."""
    return from_file(SITE_TOML)
