"""Build web-ready layers: parcels -> assigned polling place.

Reads data/raw/*.geojson (see fetch_parcels.py) and writes web/data/:
  parcels.geojson    polygons; props i, a (address), v (poll index), x, y (anchor point), d (miles)
  precincts.geojson  polygons; props n (name), v (poll index)
  polls.geojson      points;   props i, n (name), a (address), p (precincts), c (parcel count)
  meta.json          counts + QA stats
"""
import json
import math
import sys
from pathlib import Path

from shapely.geometry import MultiPolygon, Point, mapping, shape
from shapely.strtree import STRtree

ROOT = Path(sys.argv[1])
RAW, OUT = ROOT / "data" / "raw", ROOT / "web" / "data"
OUT.mkdir(parents=True, exist_ok=True)


def load(name):
    return json.load(open(RAW / f"{name}.geojson"))["features"]


def miles(lon1, lat1, lon2, lat2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(a))


def rnd(geom, nd=5):
    def r(c):
        return [round(c[0], nd), round(c[1], nd)] if isinstance(c[0], (int, float)) else [r(x) for x in c]

    g = mapping(geom)
    return {"type": g["type"], "coordinates": r(g["coordinates"])}


def clean(s):
    return (s or "").strip()


# ---------------------------------------------------------------- polling places
polls, poll_by_precinct = [], {}  # poll_by_precinct: lowercase precinct key -> poll index

jcc_pts = {f["properties"]["PRECINCT"]: shape(f["geometry"]) for f in load("jcc_polls")}
for f in sorted(load("jcc_precincts"), key=lambda f: f["properties"]["Precinct_number"]):
    p = f["properties"]
    pt = jcc_pts[p["Precinct_Name"]]
    polls.append({"n": p["Polling_Pl"], "a": "", "p": [p["Precinct_Name"]], "lon": pt.x, "lat": pt.y, "j": "James City County"})
    poll_by_precinct[p["Precinct_Name"].lower()] = len(polls) - 1

for f in load("wb_polls"):
    p = f["properties"]
    if p["VotingPrecinct"] == "Early Voting":  # Municipal Building: early voting only, not an Election Day assignment
        continue
    c = shape(f["geometry"]).centroid
    name = p["VotingPrecinct"].title()
    polls.append({"n": clean(p["BuildingName"]), "a": clean(p["PropertyAddress"]).title(), "p": [name], "lon": c.x, "lat": c.y, "j": "Williamsburg"})
    poll_by_precinct[name.lower()] = len(polls) - 1

# ---------------------------------------------------------------- precincts
precinct_feats, precinct_geoms, precinct_poll = [], [], []
for f in load("jcc_precincts"):
    v = poll_by_precinct[f["properties"]["Precinct_Name"].lower()]
    g = shape(f["geometry"]).simplify(0.00008)
    precinct_feats.append({"type": "Feature", "properties": {"n": f["properties"]["Precinct_Name"], "v": v}, "geometry": rnd(g)})
    precinct_geoms.append(shape(f["geometry"]))
    precinct_poll.append(v)
for f in load("wb_precincts"):
    name = f["properties"]["Voting_Pre"].title()
    v = poll_by_precinct[name.lower()]
    g = shape(f["geometry"]).simplify(0.00008)
    precinct_feats.append({"type": "Feature", "properties": {"n": name, "v": v}, "geometry": rnd(g)})
    precinct_geoms.append(shape(f["geometry"]))
    precinct_poll.append(v)
ptree = STRtree(precinct_geoms)

# ---------------------------------------------------------------- parcels
WB = "DBO.VW_RPT_GIS_Vision_All_Parcel_Data_Only."
raw = []  # (address, precinct attr, geometry)
for f in load("jcc_parcels"):
    if f["geometry"]:
        p = f["properties"]
        raw.append((clean(p["Full_Address"]), clean(p["PRECINCT"]).lower(), shape(f["geometry"])))
for f in load("wb_parcels"):
    if f["geometry"]:
        p = f["properties"]
        pre = clean(p[WB + "Voting_Precinct"]).lower().removesuffix(" precinct")
        raw.append((clean(p[WB + "Location"]).title(), pre, shape(f["geometry"])))

parcel_feats, per_poll = [], [0] * len(polls)
stats = {"input": len(raw), "from_attr": 0, "from_polygon": 0, "dropped": 0, "attr_vs_polygon_agree": 0, "attr_vs_polygon_checked": 0, "assigned_not_nearest": 0}

for addr, pre, geom in raw:
    if not geom.is_valid:
        geom = geom.buffer(0)
    if geom.is_empty:
        stats["dropped"] += 1
        continue
    anchor = geom.representative_point()  # always inside the parcel, unlike the centroid
    hits = ptree.query(anchor, predicate="within")
    poly_v = precinct_poll[hits[0]] if len(hits) else None

    v = poll_by_precinct.get(pre)
    if v is not None:
        stats["from_attr"] += 1
        if poly_v is not None:
            stats["attr_vs_polygon_checked"] += 1
            stats["attr_vs_polygon_agree"] += v == poly_v
    elif poly_v is not None:
        v = poly_v
        stats["from_polygon"] += 1
    else:
        stats["dropped"] += 1
        continue

    pl = polls[v]
    d = miles(anchor.x, anchor.y, pl["lon"], pl["lat"])
    nearest = min(range(len(polls)), key=lambda k: miles(anchor.x, anchor.y, polls[k]["lon"], polls[k]["lat"]))
    stats["assigned_not_nearest"] += nearest != v
    per_poll[v] += 1

    g = geom.simplify(0.00001)
    if g.is_empty:
        g = geom
    parcel_feats.append({
        "type": "Feature",
        "properties": {"i": len(parcel_feats), "a": addr, "v": v, "x": round(anchor.x, 5), "y": round(anchor.y, 5), "d": round(d, 2)},
        "geometry": rnd(g),
    })

for i, pl in enumerate(polls):
    pl["i"], pl["c"] = i, per_poll[i]

poll_feats = [
    {"type": "Feature", "properties": {k: pl[k] for k in ("i", "n", "a", "p", "j", "c")}, "geometry": {"type": "Point", "coordinates": [round(pl["lon"], 5), round(pl["lat"], 5)]}}
    for pl in polls
]
for p in poll_feats:
    p["properties"]["p"] = ", ".join(p["properties"]["p"])


def dump(name, feats):
    path = OUT / name
    json.dump({"type": "FeatureCollection", "features": feats}, open(path, "w"), separators=(",", ":"))
    print(f"{name:20s} {len(feats):6d} features  {path.stat().st_size / 1e6:6.2f} MB")


dump("parcels.geojson", parcel_feats)
dump("precincts.geojson", precinct_feats)
dump("polls.geojson", poll_feats)

stats["parcels_out"] = len(parcel_feats)
stats["pct_not_nearest"] = round(100 * stats["assigned_not_nearest"] / len(parcel_feats), 1)
json.dump(stats, open(OUT / "meta.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
