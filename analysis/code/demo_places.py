"""Places a trip can start or end at, with walking and cycling minutes along the path network.

Usage: python demo_places.py DATA_DIR OUT_JSON [--radius 2600]

The page used to measure every walk as a straight line times 1.25. Between the campus and the metro the way leads
through a tunnel and around a hill, so this script asks an OSRM server (routing.openstreetmap.de, profiles "foot"
and "bike", data (c) OpenStreetMap contributors) for the path length between every pair of nodes and writes
OUT_JSON (docs/places.json):

  nodes   the places below (campus buildings, the metro station, the ferry pier), then every logged station within
          --radius metres of the campus centre
  walk    minutes on foot from node a to node b at 80 m/min, one row per node, one character per value (A64)
  ride    minutes by bike at 200 m/min, same layout

A path is at least the straight line and at most 1.7 straight lines long: some footpaths inside the campus are
missing from the map, and the router then walks around a block to connect two stations 70 m apart. Slopes are not
modelled. Place coordinates are the centres of the buildings in OpenStreetMap. The script needs the network and is
run by hand when the list of places or stations changes; the page and the analysis read its output.
"""
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from nsysu_data import CAMPUS, GATEWAY, load_stations  # noqa: E402

DATA, OUT = Path(sys.argv[1]), Path(sys.argv[2])
ARG = lambda name, default, cast: cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
RADIUS = ARG("--radius", 2600, int)
SERVER = "https://routing.openstreetmap.de/routed-{p}/table/v1/{p}/{coords}?annotations=duration,distance"
A64 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_"
WALK_M_PER_MIN = 80.0            # walking pace
RIDE_M_PER_MIN = 200.0           # 12 km/h: a campus with slopes and people on the paths
DETOUR_CAP = 1.7                 # a path longer than this many straight lines is taken to be a gap in the map, not a detour
PLACES = [  # id, name, English name, lat, lng, group
    ("lib", "圖資大樓", "Library", 22.62741, 120.26586, "campus"),
    ("cm", "管理學院", "College of Management", 22.62752, 120.26529, "campus"),
    ("eng", "工學院", "College of Engineering", 22.62723, 120.26617, "campus"),
    ("ee", "電資大樓", "EE Building", 22.62725, 120.26752, "campus"),
    ("sci", "理學院", "College of Science", 22.62568, 120.26638, "campus"),
    ("ss", "社科院", "Social Sciences", 22.62558, 120.26530, "campus"),
    ("adm", "行政大樓", "Administration", 22.62586, 120.26582, "campus"),
    ("gym", "體育館", "Gymnasium", 22.62478, 120.26627, "campus"),
    ("ir", "國研大樓", "International Building", 22.62385, 120.26607, "campus"),
    ("sc", "學生活動中心", "Student Center", 22.62835, 120.26505, "campus"),
    ("wl", "武嶺山莊", "Wuling Dorms", 22.62968, 120.26385, "campus"),
    ("ch", "翠亨山莊", "Cuiheng Dorms", 22.62837, 120.26829, "campus"),
    ("ms", "海科院", "Marine Sciences", 22.63123, 120.26179, "campus"),
    ("la", "文學院", "Liberal Arts", 22.63458, 120.26097, "campus"),
    ("krt", "捷運哈瑪星站", "KRT Sizihwan Sta.", 22.62191, 120.27337, "town"),
    ("ferry", "鼓山輪渡站", "Gushan Ferry Pier", 22.61987, 120.27001, "town"),
]


def table(profile, pts):
    coords = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in pts)
    req = urllib.request.Request(SERVER.format(p=profile, coords=coords), headers={"User-Agent": "nsysu-youbike-log (course project, github.com/alexlin8888/nsysu-youbike-log)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                d = json.load(r)
            if d.get("code") == "Ok":
                return np.array(d["distances"], float), np.array([w["distance"] for w in d["sources"]], float)
            raise RuntimeError(d.get("code"))
        except Exception as exc:  # noqa: BLE001
            print(f"{profile}: attempt {attempt + 1} failed ({exc})", flush=True)
            time.sleep(5 * (attempt + 1))
    raise SystemExit(f"no answer from the {profile} server")


st = load_stations(DATA)
st = st[(st.logged == 1) & (st.dist_m <= RADIUS)].sort_values("dist_m").reset_index(drop=True)
pts = [(p[3], p[4]) for p in PLACES] + list(zip(st.lat, st.lng))
n = len(pts)
la, lo = np.radians([p[0] for p in pts]), np.radians([p[1] for p in pts])
line = 6371000 * np.hypot(np.subtract.outer(la, la), np.subtract.outer(lo, lo) * math.cos(math.radians(22.626)))     # straight-line metres
out = {"generated": time.strftime("%Y-%m-%d"), "source": "path lengths from the OSRM foot and bike profiles on routing.openstreetmap.de; data (c) OpenStreetMap contributors",
       "radius_m": RADIUS, "walk_m_per_min": WALK_M_PER_MIN, "ride_m_per_min": RIDE_M_PER_MIN, "detour_cap": DETOUR_CAP,
       "places": [{"id": p[0], "name": p[1], "name_en": p[2], "lat": p[3], "lng": p[4], "group": p[5]} for p in PLACES],
       "stations": list(st.sno)}
for profile, key, pace in (("foot", "walk", WALK_M_PER_MIN), ("bike", "ride", RIDE_M_PER_MIN)):
    dist, snap = table(profile, pts)
    if np.isnan(dist).any():
        raise SystemExit(f"{profile}: {int(np.isnan(dist).sum())} pairs have no route")
    path = dist + snap[:, None] + snap[None, :]                    # door (dock) to the path, the path, the path to the door
    capped = np.clip(path, line, DETOUR_CAP * line)
    mins = np.maximum(1.0, capped / pace)
    np.fill_diagonal(mins, 0.0)
    out[key] = ["".join(A64[min(63, int(round(v)))] for v in row) for row in mins]
    off = ~np.eye(n, dtype=bool) & (line > 150)
    print(f"{profile}: {n} nodes, median {np.median(mins[off]):.1f} min, path / straight line {np.median(path[off] / line[off]):.2f} "
          f"(90th pct {np.percentile(path[off] / line[off], 90):.2f}), pairs at the cap {(path[off] > DETOUR_CAP * line[off]).mean():.1%}, "
          f"largest snap {snap.max():.0f} m, over 63 min: {int((mins > 63).sum())}", flush=True)
    time.sleep(2)
json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
print(f"wrote {OUT}: {len(PLACES)} places, {len(st)} stations, {OUT.stat().st_size / 1024:.0f} kB")
