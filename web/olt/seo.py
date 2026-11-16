"""Sitemap, robots.txt and the JSON-LD Dataset description."""
import html
import os

from . import common


# The files under /data/ listed as the dataset's distribution: (name, media type).
DISTRIBUTION = (
    ("trails.csv", "text/csv"),
    ("trails.json", "application/json"),
    ("index.geojson", "application/geo+json"),
    ("overview.geojson", "application/geo+json"),
    ("all-gpx.zip", "application/zip"),
    ("all-geojson.zip", "application/zip"),
)


def dataset_jsonld(records, site):
    """One schema.org Dataset block for the home page and /data/."""
    dist = []
    for name, fmt in DISTRIBUTION:
        url = site.canonical(f"/data/{name}") or f"/data/{name}"
        dist.append({"@type": "DataDownload", "name": name, "encodingFormat": fmt, "contentUrl": url})
    obj = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": site.name,
        "description": site.tagline,
        "license": "https://creativecommons.org/publicdomain/zero/1.0/",
        "distribution": dist,
        "variableMeasured": ["length_km", "country", "regions", "source licence"],
    }
    if site.base_url:
        obj["url"] = site.canonical("/")
    return obj


def sitemap_xml(paths, site):
    """sitemap.xml text for site paths; caller checks site.base_url is set."""
    urls = "".join(
        f"  <url><loc>{html.escape(site.canonical(p), quote=True)}</loc></url>\n"
        for p in paths)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}</urlset>\n")


def robots_txt(site):
    lines = ["User-agent: *", "Allow: /", ""]
    if site.base_url:
        lines.append(f"Sitemap: {site.canonical('/sitemap.xml')}")
    return "\n".join(lines).rstrip() + "\n"


def write_seo_files(out_dir, paths, site):
    """Write robots.txt always and sitemap.xml only with a base_url."""
    with open(os.path.join(out_dir, "robots.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(robots_txt(site))
    sitemap = os.path.join(out_dir, "sitemap.xml")
    if site.base_url:
        with open(sitemap, "w", encoding="utf-8", newline="\n") as f:
            f.write(sitemap_xml(paths, site))
    elif os.path.isfile(sitemap):
        os.remove(sitemap)  # a stale sitemap with wrong URLs is worse than none


def all_paths(records, region_paths):
    """Every indexable page path, in nav order then record pages."""
    paths = ["/", "/regions/"] + list(region_paths) + [
        "/routes/", "/sources/", "/logos/", "/about/", "/data/",
        "/data/schema/", "/data/changelog/", "/left-out/"]
    paths += [common.trail_path(r) for r in sorted(records, key=lambda r: r["id"])]
    return paths
