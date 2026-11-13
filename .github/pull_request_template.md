## What changed

<!-- Which trail (its record id), which fields or files, and why. -->

## Checklist

- [ ] One trail per pull request, where practical, and only that trail's directory changed.
- [ ] The validator passes: `python3 tools/build_index.py`, then `python3 tools/validate.py` prints `OK <n> trails`.
- [ ] The source for each changed fact is named (where it can be checked: a source page, a map, or a measured track).
- [ ] A track is included only where its source's terms allow it to be passed on (`redistributable` is `true` for every included file; see `docs/schema.md`). OpenStreetMap tracks carry the credit "© OpenStreetMap contributors" under the ODbL. Where a publisher's track may not be passed on, no track is included and the record says why (`source.line_absent_reason`).
- [ ] For a person-defined route, the track follows the creator's choice (`route.line_policy`): no track is included from any source, OpenStreetMap included, where the creator sells the route, withholds the track, or the position is not settled.
- [ ] `release.txt` is updated where track files changed (source, licence, date read), and any logo names its holder (`shield.logo_owner`) and where the art came from (`shield.logo_source`).
