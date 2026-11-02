# Day 02 · Lines: Line to the ballot box

Hover a parcel in James City County / Williamsburg, VA to draw a line to its assigned Election Day polling place.

## Run
```
cd web && python3 -m http.server 8765   # then open http://localhost:8765
```
The site is static (MapLibre GL JS + CARTO dark basemap, no API keys), so `web/` can be dropped on GitHub Pages as is.

## Rebuild the data
```
python3 -I scripts/fetch_parcels.py data/raw                    # parcels, paged from the county/city ArcGIS REST services
python3 scripts/build_data.py "$PWD"                            # needs `pip install shapely`; writes web/data/*
```
`data/raw/{jcc,wb}_polls.geojson` and `{jcc,wb}_precincts.geojson` are small and committed. They were pulled with a single `query?where=1=1&outFields=*&outSR=4326&f=geojson` per layer. The large `*_parcels.geojson` downloads are git-ignored and recreated by `fetch_parcels.py`.

## Sources
- JCC: `property.jamescitycountyva.gov/arcgis/rest/services/JCC/GIS_Data` (FeatureServer/17 parcels; MapServer/25 polling places, /26 precincts). The MapServer parcel layer returns no geometry, so use the FeatureServer.
- Williamsburg: `gis.williamsburgva.gov/server/rest/services` (`Tax_Parcels`, `Voter_Precinct_Lookup_Map_MIL1`).

## Method and QA
- A parcel's polling place comes from its `PRECINCT` attribute (county) / `Voting_Precinct` (city), then a precinct to polling-place lookup.
- Parcels missing a precinct fall back to a point-in-polygon test; 7 of 42,023 could not be placed and are dropped.
- QA: attribute vs. precinct polygon agree for 41,992 of 42,003 parcels (99.97%).
- Line start = a point guaranteed inside the parcel (`representative_point`), end = polling place. Distances are great-circle, not driving routes.
- Williamsburg polling sites are building polygons in the source, so they are drawn at the polygon centroid.
- The City Municipal Building is early-voting only and is excluded.
- Owner and sale data are deliberately not requested.

## License
The code is released under the [MIT License](LICENSE). The parcel, precinct and polling-place data come from James City County and City of Williamsburg GIS and remain subject to those sources' own terms; the MIT license does not cover them.

## Disclaimer
**This is an unofficial demo and is not affiliated with or endorsed by James City County, the City of Williamsburg or the Virginia Department of Elections.** It was built with the help of AI and may contain errors, so use it with caution.

- Precincts, polling places and parcels were pulled from county and city GIS services on 2 Nov 2026 and may be out of date or incomplete.
- A parcel's polling place is based on the precinct recorded for the parcel, not on any individual's voter registration.
- Lines are straight, not driving routes. Early-voting sites are not shown.
- **Do not rely on this map to decide where to vote.** Confirm your polling place at [vote.elections.virginia.gov](https://vote.elections.virginia.gov/VoterInformation) or with your local registrar.
- The software is provided "as is", without warranty of any kind (see [LICENSE](LICENSE)).
