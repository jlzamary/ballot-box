# Day 02 · Lines: Line to the ballot box

Hover a parcel in James City County / Williamsburg, VA to draw a line to its assigned Election Day polling place.

## Run
```
cd web && python3 -m http.server 8765   # then open http://localhost:8765
```
The site is static (MapLibre GL JS + CARTO light/dark basemaps, no API keys), so `web/` can be dropped on GitHub Pages as is.

## Rebuild the data
```
python3 -I scripts/fetch_parcels.py data/raw                    # parcels, paged from the county/city ArcGIS REST services
python3 scripts/build_data.py "$PWD"                            # needs `pip install shapely`; writes web/data/*
```
`data/raw/{jcc,wb}_polls.geojson` and `{jcc,wb}_precincts.geojson` are small and committed. They were pulled with a single `query?where=1=1&outFields=*&outSR=4326&f=geojson` per layer. The large `*_parcels.geojson` downloads are git-ignored and recreated by `fetch_parcels.py`.

## Data sources
All election data was retrieved from the publishers' public ArcGIS REST services on **2 Nov 2026**. Nothing was scraped from third-party aggregators, and no owner, sale or valuation fields were requested.

| Data | Publisher | Source layer | Fields used |
|---|---|---|---|
| James City County parcels (36,479) | James City County GIS | [GIS_Data / FeatureServer / 17 "Parcels"](https://property.jamescitycountyva.gov/arcgis/rest/services/JCC/GIS_Data/FeatureServer/17) | geometry, `Full_Address`, `PRECINCT`, `POLL`, `PIN` |
| James City County polling places (18) | James City County GIS | [GIS_Data / MapServer / 25 "Polling Places"](https://property.jamescitycountyva.gov/arcgis/rest/services/JCC/GIS_Data/MapServer/25) | point location, `NAME`, `PRECINCT` |
| James City County voting precincts (18) | James City County GIS | [GIS_Data / MapServer / 26 "Voting Precincts"](https://property.jamescitycountyva.gov/arcgis/rest/services/JCC/GIS_Data/MapServer/26) | geometry, `Precinct_Name`, `Precinct_number`, `Polling_Pl` |
| Williamsburg parcels (5,544 records) | City of Williamsburg GIS | [Tax_Parcels / MapServer / 0](https://gis.williamsburgva.gov/server/rest/services/Tax_Parcels/MapServer/0) | geometry, `Location`, `Voting_Precinct` |
| Williamsburg polling sites (3, one is early-voting only) | City of Williamsburg GIS | [Voter_Precinct_Lookup_Map_MIL1 / MapServer / 0 "Polling_Sites"](https://gis.williamsburgva.gov/server/rest/services/Voter_Precinct_Lookup_Map_MIL1/MapServer/0) | building polygon, `VotingPrecinct`, `BuildingName`, `PropertyAddress` |
| Williamsburg voting precincts (2) | City of Williamsburg GIS | [Voter_Precinct_Lookup_Map_MIL1 / MapServer / 1 "VotingPrecincts2023"](https://gis.williamsburgva.gov/server/rest/services/Voter_Precinct_Lookup_Map_MIL1/MapServer/1) | geometry, `Voting_Pre` |
| Basemap tiles and style | [CARTO](https://carto.com/basemaps) (Dark Matter and Positron), built on data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) | loaded at runtime from `basemaps.cartocdn.com` | n/a |
| Map rendering library | [MapLibre GL JS](https://maplibre.org/) 4.7.1 | loaded at runtime from cdnjs | n/a |

Notes:
- The county's MapServer parcel layer (`GIS_Data/MapServer/17`) returns attributes with no geometry, so the script uses the FeatureServer version of the same layer.
- The county's [open data portal](https://opendata-jcc.opendata.arcgis.com/) is the publisher's general entry point to its GIS data.
- Where the county layer has no polling-place street address, the map shows none rather than guessing. Only the Williamsburg sites carry an address in the source.
- To check your own polling place, use the state's lookup instead of this map: [vote.elections.virginia.gov](https://vote.elections.virginia.gov/VoterInformation). It is a verification tool, not a data source here.

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
