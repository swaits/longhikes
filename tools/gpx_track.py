#!/usr/bin/env python3
"""Turn a holder's GPX file into a trail's track files.

Reads a GPX file (1.0 or 1.1) and writes, in the trail's directory:

    line.geojson   one LineString per track segment, in file order
    release.txt    source, licence, attribution and date read

Only geometry is kept: longitude and latitude of each track point, rounded to
6 decimal places. Elevations, timestamps, point and track names, descriptions,
comments, links, extensions, device and author metadata are read past and
never written. Waypoints and routes are counted and reported, not written.

Python standard library only. Run from anywhere:
    python3 tools/gpx_track.py FILE.gpx --id TRAIL_ID --source TEXT --licence TEXT --attribution TEXT
    python3 tools/gpx_track.py FILE.gpx --id TRAIL_ID --dry     print figures only
    python3 tools/gpx_track.py FILE.gpx --id TRAIL_ID --out DIR write to DIR/TRAIL_ID
    python3 tools/gpx_track.py FILE.gpx --id TRAIL_ID --force   replace existing files
    python3 tools/gpx_track.py FILE.gpx --id TRAIL_ID --route-name NAME
                                                                set the feature's route_name

Segments are joined in order: tracks in file order, segments within a track in
order, each segment one LineString (the files hoosier-heritage-trail and
black-canyon use). Nothing is reordered or reversed. The run prints tracks,
segments, points, waypoints, the measured length (the validator's own rule),
the parts left after joining ends within 100 m (the rule tools/elevation.py
uses), and every gap between consecutive segments larger than --gap-km
(default 1 km) with its size and where it lies. A file that is not GPX (an
HTML page saved with a .gpx ending, say) is refused. XML with a DOCTYPE is
refused, so no entity can be expanded.

--source, --licence and --attribution are the lines of release.txt. The output
depends only on the file and the options (release.txt carries the date read).
"""
import argparse
import datetime
import importlib.util
import json
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAP_KM_DEFAULT = 1.0


class TrackError(Exception):
    """A reason to stop, shown to the user without a traceback."""


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


haversine_km = _load("validate_for_gpx_track", "validate.py").haversine_km
join_parts = _load("osm_track_for_gpx_track", "osm_track.py").join_parts
JOIN_GAP_M = 100.0


def _local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def parse(data):
    """GPX bytes -> dict: tracks (list of lists of segments of [lon, lat]),
    waypoints, routes. Raises TrackError if it is not a GPX file."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    head = data[:4096].lstrip().lower()
    if b"<!doctype" in head[:4096] and b"<!doctype html" in head:
        raise TrackError("the file is an HTML page, not GPX")
    if b"<!doctype" in data[:65536].lower() or b"<!entity" in data[:65536].lower():
        raise TrackError("the file has a DOCTYPE or entity declaration; refused")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise TrackError(f"the file is not well-formed XML ({e})") from e
    if _local(root.tag) != "gpx":
        raise TrackError(f"the root element is {_local(root.tag)!r}, not gpx")
    tracks, waypoints, routes = [], 0, 0
    for el in root:
        kind = _local(el.tag)
        if kind == "wpt":
            waypoints += 1
        elif kind == "rte":
            routes += 1
        elif kind == "trk":
            segs = []
            for seg in el:
                if _local(seg.tag) != "trkseg":
                    continue
                pts = []
                for p in seg:
                    if _local(p.tag) != "trkpt":
                        continue
                    try:
                        lat, lon = float(p.get("lat")), float(p.get("lon"))
                    except (TypeError, ValueError) as e:
                        raise TrackError("a track point has no valid lat/lon") from e
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        raise TrackError(f"a track point is out of range ({lat}, {lon})")
                    pt = [round(lon, 6), round(lat, 6)]
                    if not pts or pts[-1] != pt:     # drop repeats of the same point
                        pts.append(pt)
                if len(pts) >= 2:
                    segs.append(pts)
            tracks.append(segs)
    segments = [s for t in tracks for s in t]
    if not segments:
        raise TrackError("the file has no track segment with two or more points")
    return {"tracks": tracks, "segments": segments, "waypoints": waypoints,
            "routes": routes}


def figures(parsed, gap_km=GAP_KM_DEFAULT):
    segs = parsed["segments"]
    gaps = []
    for i in range(len(segs) - 1):
        a, b = segs[i][-1], segs[i + 1][0]
        d = haversine_km([a, b])
        if d > gap_km:
            gaps.append({"after_segment": i + 1, "km": d, "from": a, "to": b})
    return {"tracks": len(parsed["tracks"]), "segments": len(segs),
            "points": sum(len(s) for s in segs), "waypoints": parsed["waypoints"],
            "routes": parsed["routes"],
            "measured_km": sum(haversine_km(s) for s in segs),
            "parts": len(join_parts(segs)), "gaps": gaps}


def geojson_text(segments, route_name=None):
    props = {"route_name": route_name} if route_name else {}
    feats = [json.dumps({"type": "Feature", "properties": props,
                         "geometry": {"type": "LineString", "coordinates": s}},
                        separators=(",", ":"), ensure_ascii=False) for s in segments]
    return '{"type":"FeatureCollection","features":[' + ",".join(feats) + "]}\n"


def release_text(source, licence, attribution, date, fig):
    return (f"Source: {source}\n"
            f"Licence: {licence}\n"
            f"Attribution: {attribution}\n"
            f"Source read: {date}\n"
            f"Published copy: the {fig['segments']} track segment"
            f"{'s' if fig['segments'] != 1 else ''} of the GPX file ({fig['points']:,} points) "
            "as LineStrings in file order; geometry only (longitude and latitude, no "
            "elevation, time, name or other metadata); coordinates rounded to 6 decimal "
            "places and written as compact JSON.\n")


def run(args, today=None, out=print):
    tdir = os.path.join(os.path.abspath(args.out), args.id)
    if not os.path.isdir(tdir):
        raise TrackError(f"{tdir} does not exist: create the trail directory and "
                         "trail.toml first")
    names = ("line.geojson", "release.txt")
    if not args.dry and not args.force:
        have = [n for n in names if os.path.exists(os.path.join(tdir, n))]
        if have:
            raise TrackError(f"{', '.join(have)} already in {tdir}: use --force to replace")
    if not args.dry and not (args.source and args.licence and args.attribution):
        raise TrackError("--source, --licence and --attribution are needed to write release.txt")
    with open(args.gpx, "rb") as f:
        parsed = parse(f.read())
    fig = figures(parsed, args.gap_km)
    out(f"tracks: {fig['tracks']}")
    out(f"segments: {fig['segments']}")
    out(f"points: {fig['points']}")
    out(f"waypoints: {fig['waypoints']} (not written)")
    out(f"routes: {fig['routes']} (not written)")
    out(f"measured_km: {fig['measured_km']:.1f}")
    out(f"parts (ends within {JOIN_GAP_M:.0f} m): {fig['parts']}")
    for g in fig["gaps"]:
        out(f"gap after segment {g['after_segment']}: {g['km']:.1f} km "
            f"from ({g['from'][1]}, {g['from'][0]}) to ({g['to'][1]}, {g['to'][0]})")
    if args.dry:
        out("dry run: nothing written")
        return fig
    date = (today or datetime.date.today()).isoformat()
    files = {"line.geojson": geojson_text(parsed["segments"], args.route_name),
             "release.txt": release_text(args.source, args.licence, args.attribution,
                                         date, fig)}
    for name, text in files.items():
        with open(os.path.join(tdir, name), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    out("wrote " + ", ".join(files) + f" in {tdir}")
    return fig


def main(argv=None):
    ap = argparse.ArgumentParser(description="Turn a GPX file into a trail's track files.")
    ap.add_argument("gpx", help="the GPX file")
    ap.add_argument("--id", required=True, help="trail id (the directory name)")
    ap.add_argument("--out", default=ROOT, help="directory holding the trail directories "
                    "(default: the repository root)")
    ap.add_argument("--source", help="release.txt Source line")
    ap.add_argument("--licence", help="release.txt Licence line")
    ap.add_argument("--attribution", help="release.txt Attribution line")
    ap.add_argument("--route-name", help="route_name property of the features")
    ap.add_argument("--gap-km", type=float, default=GAP_KM_DEFAULT,
                    help="report gaps between segments larger than this (default 1)")
    ap.add_argument("--dry", action="store_true", help="print the figures, write nothing")
    ap.add_argument("--force", action="store_true", help="replace existing files")
    args = ap.parse_args(argv)
    try:
        run(args)
    except (TrackError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
