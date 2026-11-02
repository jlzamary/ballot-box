"""Download JCC + Williamsburg parcels (paged) as GeoJSON in EPSG:4326.

Only the fields needed for the map are requested (no owner / sale data).
Geometry is lightly generalized server-side (~1 m) to keep the file small.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAW = Path(sys.argv[1])
RAW.mkdir(parents=True, exist_ok=True)

JCC = "https://property.jamescitycountyva.gov/arcgis/rest/services/JCC/GIS_Data/FeatureServer/17"  # MapServer/17 returns attributes only
WB = "https://gis.williamsburgva.gov/server/rest/services/Tax_Parcels/MapServer/0"
WB_PFX = "DBO.VW_RPT_GIS_Vision_All_Parcel_Data_Only."

SOURCES = {
    "jcc_parcels": (JCC, "PIN,Full_Address,PRECINCT,POLL", "OBJECTID"),
    "wb_parcels": (
        WB,
        f"{WB_PFX}GPIN,{WB_PFX}Location,{WB_PFX}Voting_Precinct",
        "DBO.Tax_Parcels_Test.OBJECTID",
    ),
}


def get(url, params, tries=4):
    data = urllib.parse.urlencode(params).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "30DayMapChallenge-Day02 (personal project)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print("  retry", i, e, file=sys.stderr)
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed: {url}")


for name, (layer, fields, oid) in SOURCES.items():
    ids = get(layer + "/query", {"where": "1=1", "returnIdsOnly": "true", "f": "json"})
    oid_field = ids["objectIdFieldName"]
    oids = sorted(ids["objectIds"])
    print(name, len(oids), "features")
    feats = []
    for i in range(0, len(oids), 1000):
        chunk = oids[i : i + 1000]
        d = get(
            layer + "/query",
            {
                "objectIds": ",".join(map(str, chunk)),
                "outFields": fields,
                "outSR": 4326,
                "returnGeometry": "true",
                "maxAllowableOffset": 0.00001,
                "geometryPrecision": 6,
                "f": "geojson",
            },
        )
        feats += d["features"]
        print(f"  {len(feats)}/{len(oids)}")
    json.dump({"type": "FeatureCollection", "features": feats}, open(RAW / f"{name}.geojson", "w"))
