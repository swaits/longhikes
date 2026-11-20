# Setting a season by judgement

Where no page states a season, it is set by a reviewer from a packet, and the method was tested blind against the seasons that pages state. This page is the reviewer's instruction and the record of the test. The tools are `tools/season_judge.py` (packets, scoring, staging) and `tools/estimate_season.py` (the machine estimate that is one input, and the monthly check).

## The test

The reviewers also estimated every trail whose season a page states, from packets identical in form with the season hidden: the trail's own timing sentences were removed, and its comparable trails were never dealt to the same part as it. The three parts were reviewed separately, and the figures are added together. The result is in `tools/season_blind_test.json`, which the site reads; `python3 tools/season_judge.py score <answer files> --write tools/season_blind_test.json` produces it. A season "matches" when each end of the reviewer's months is within one month of the stated season's, on the circle of the year. The machine estimate on its own matches 67.6 percent on the same measure, under the 75 percent bar, so it is not written to a record; the judged method passes, and its confidence labels are honest: high matches most often, low least.

## What a packet lacks

The packets rebuilt by `tools/season_judge.py packets` carry the monthly high temperature at the high and low ground but give monthly precipitation only when a file of it is supplied (`--precip`); the packets the reviewers read in November 2026 carried it for every trail.

## The reviewer's instruction


You will estimate the hiking season for each trail on a list you are given (one of `part-1.txt`, `part-2.txt` or `part-3.txt`). For each id there is one packet, `packets/<id>.md`. Work only on the ids in your list, and read only the packet for the id you are estimating.

## What to estimate

The months a typical hiker normally walks the whole trail, or thru-hikes it, in a normal year.

- A season may be two windows (spring and fall) or wrap the year end (October to April).
- A month counts when about half of it or more is in season.
- Think about what actually sets the season there: snow on the high ground, summer heat, monsoon, humidity and bugs, hunting season, short daylight, river levels, mud.
- People do walk in cold and snow in places where that is normal. Do not assume summer everywhere.

## Rules

1. Use only the packet and your own general knowledge of the region and of the trail.
2. Do not open any trail record, do not search the web, and do not read any file outside the packet and this README.
3. Do not look at other trails' packets, answers or any scores.

## What a packet contains

- **The trail:** id, name, common name, country, states or provinces, length in miles, kind, shape, terrain, travel (on trail or cross-country), high point and typical days where on file.
- **Summary, start and end:** from the trail's record, with every sentence that bears on timing removed.
- **Where it is:** southernmost and northernmost latitude and westernmost and easternmost longitude of the sample points, and whether the location comes from a real track, from start and end points only, or from a region-centre fallback (the least precise).
- **Elevation:** high ground and low ground in feet as the climate was read, and the track's highest and lowest points where there is a track.
- **Climate normals (1981 to 2010):** for each month, the mean daily high in degrees F at the high ground (the upper quarter of the sample points) and the low ground (the lower half), and monthly precipitation in inches at both. Temperatures are modelled and lapse-corrected, so treat them as a guide.
- **Machine estimate:** a climate model's estimated months, right about two times in three. Use it as one input, not an answer.
- **Comparable trails:** ten trails with a season on record, chosen as most similar in climate and nearest in place, with state, high ground elevation, and each one's season and months. They are neighbours, not copies: yours may differ for good reason.
- **What pages say:** present for a few trails only, where published pages disagree: each page's publisher and the months it gives.

## Answer format

One tab-separated file, `an answer file named by whoever runs the review (for example `answers/<yourname>.tsv`)`, one line per trail on your list, no header, five columns:

1. id
2. months, as comma-separated numbers 1 to 12 (e.g. `7,8,9`, or `3,4,5,9,10,11`, or `10,11,12,1,2,3,4`)
3. season phrase (e.g. `July to September`, `Spring and fall`)
4. confidence: `high`, `medium` or `low`
5. one sentence: what sets the season there

Rules for the file: every id on your list exactly once; never an empty month list; no tabs inside a column; no extra columns. Say low when you really do not know.
