# Notice

## Logos and marks

The files `shield.svg` and `shield.png` in the trail directories are the logos and marks of the trails they identify. Each logo belongs to the holder named in that trail's record (`shield.logo_owner` in `trail.toml`, with where the art was taken from in `shield.logo_source`).

The logos are included only to identify each trail. They are not covered by this repository's licences (CC0-1.0 for the records and documents, MIT for the tools, or the source licences that cover the tracks). No right to use a logo for any other purpose is given or implied.

Some logos are official emblems of United States National Scenic or Historic Trails. Those emblems are federal insignia; this repository's use of them is for identification only.

## Removal

A holder who wants a logo removed, replaced or credited differently can ask by opening an issue in this repository, or by writing to the repository maintainers through the contact shown on the repository's main page. Say which trail and which file. The file will be removed or replaced, and the record will be updated to say so.

The same applies to a person-defined route. A route's creator can ask for its record to be corrected or removed, and the record will be corrected or removed. Say which route.

## Data

Tracks keep the terms of their sources. See each trail's record and SOURCES.md. In particular, tracks from OpenStreetMap are © OpenStreetMap contributors and are available under the Open Database License (ODbL): https://www.openstreetmap.org/copyright

## Elevation

The files `elevation.json` in the trail directories are computed from each trail's track and the Terrain Tiles open elevation data (https://registry.opendata.aws/terrain-tiles/), which Mapzen made from several public sources. The data is used under the terms it states (https://github.com/tilezen/joerd/blob/master/docs/attribution.md, read 2026-11-13). Each `elevation.json` carries the credit in its `source.attribution`, and a page that shows elevation from these files shows it too:

- United States 3DEP (formerly NED) and global GMTED2010 and SRTM terrain data courtesy of the U.S. Geological Survey.
- Canada terrain data contains information licensed under the Open Government Licence - Canada.
- ArcticDEM terrain data DEM(s) were created from DigitalGlobe, Inc., imagery and funded under National Science Foundation awards 1043681, 1559691, and 1542736.
- Global ETOPO1 terrain data U.S. National Oceanic and Atmospheric Administration.
- Terrain Tiles was accessed from https://registry.opendata.aws/terrain-tiles.

## Climate

A season marked as estimated is worked out from monthly climate at the trail's elevation. The climate values are monthly means of daily maximum temperature for 1981 to 2010 from CHELSA V2.1 (https://www.chelsa-climate.org/datasets/chelsa_climatologies, released under CC0 1.0), read by `tools/season_climate.py`, with grid elevation from NOAA's ETOPO 2022 relief model (unrestricted version, https://www.ncei.noaa.gov/products/etopo-global-relief-model). CHELSA asks for this citation: Karger, D. N., Conrad, O., Boehner, J., Kawohl, T., Kreft, H., Soria-Auza, R. W., Zimmermann, N. E., Linder, H. P., Kessler, M. (2017). Climatologies at high resolution for the earth's land surface areas. Scientific Data 4, 170122, https://doi.org/10.1038/sdata.2017.122. Only the estimated seasons derive from it. Each estimated record names it in its sources, and the estimates themselves say they are estimates wherever they are shown.
