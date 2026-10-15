"""NTU data pipeline: open Taipei trip records + 10-minute inventory snapshots -> analysis tables.

Usage
  python ntu_pipeline.py stations   SITES_CSV OUT_DIR
  python ntu_pipeline.py trips      RAW_DIR OUT_DIR            (monthly zips YYYYMM.zip)
  python ntu_pipeline.py snapshots  SNAP_REPO OUT_DIR START END (git sparse clone; reads data/slots/*.csv via git cat-file)
  python ntu_pipeline.py reconcile  OUT_DIR

Outputs in OUT_DIR
  ntu_stations.csv      study-area stations (<= RADIUS_M from the NTU campus centroid), campus flag
  trips_YYYYMM.parquet  trips with rent or return station in the study area (hour-resolution times)
  flows_hourly.parquet  per station x hour: rentals, returns (study area)
  panel_10min.parquet   per station x 10-min slot: bikes, docks, total (forward-filled snapshots)
  hourly.parquet        per station x hour: stock at start/end, rentals, returns, residual, move flag, exposure
"""
import io
import math
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RADIUS_M = 1200
TRIP_COLS = ["rent_time", "rent_st", "return_time", "return_st", "dur", "bike", "date"]


def dist_m(lat, lng, lat0, lng0):
    p = math.pi / 180
    return 6371000 * math.hypot((lat - lat0) * p, (lng - lng0) * p * math.cos(lat0 * p))


def cmd_stations(sites_csv, out):
    s = pd.read_csv(sites_csv, dtype={"sno": str})
    s["name"] = s.sna.str.replace("YouBike2.0_", "", regex=False).str.strip()
    campus = s[s.sarea == "臺大公館校區"]
    lat0, lng0 = campus.latitude.mean(), campus.longitude.mean()
    s["dist_m"] = [int(dist_m(a, b, lat0, lng0)) for a, b in zip(s.latitude, s.longitude)]
    st = s[s.dist_m <= RADIUS_M].copy()
    st["campus"] = (st.sarea == "臺大公館校區").astype(int)
    st = st[["sno", "name", "sarea", "latitude", "longitude", "dist_m", "campus", "act"]].sort_values("dist_m")
    st.to_csv(out / "ntu_stations.csv", index=False)
    print(f"{len(st)} stations within {RADIUS_M} m ({st.campus.sum()} on campus); centroid {lat0:.4f},{lng0:.4f}")


def cmd_trips(raw, out):
    st = pd.read_csv(out / "ntu_stations.csv", dtype={"sno": str})
    name2sno = dict(zip(st.name, st.sno))
    names = set(name2sno)
    flows = []
    for z in sorted(raw.glob("*.zip")):
        ym = z.stem
        if (out / f"trips_{ym}.parquet").exists():
            print("skip", ym); continue
        kept = []
        with zipfile.ZipFile(z) as zf:
            inner = zf.namelist()[0]
            with zf.open(inner) as fh:
                for chunk in pd.read_csv(fh, header=None, encoding="utf-8", encoding_errors="replace",
                                         chunksize=1_000_000, dtype=str):
                    # 2024 files have 6 columns (no bike-type column); 2025 files have 7
                    chunk.columns = TRIP_COLS if chunk.shape[1] == 7 else [c for c in TRIP_COLS if c != "bike"]
                    if "bike" not in chunk:
                        chunk["bike"] = ""
                    chunk["rent_st"] = chunk.rent_st.str.strip()
                    chunk["return_st"] = chunk.return_st.str.strip()
                    m = chunk.rent_st.isin(names) | chunk.return_st.isin(names)
                    kept.append(chunk[m])
        t = pd.concat(kept, ignore_index=True)
        t["rent_time"] = pd.to_datetime(t.rent_time, errors="coerce")
        t["return_time"] = pd.to_datetime(t.return_time, errors="coerce")
        t["rs"] = t.rent_st.map(name2sno)
        t["ts"] = t.return_st.map(name2sno)
        d = pd.to_timedelta(t.dur, errors="coerce")
        t["dur_min"] = d.dt.total_seconds() / 60
        t["ebike"] = (t.bike == "電輔車").astype(np.int8)
        t = t[["rent_time", "rs", "return_time", "ts", "dur_min", "ebike"]].dropna(subset=["rent_time", "return_time"])
        t.to_parquet(out / f"trips_{ym}.parquet", index=False)
        r = t.dropna(subset=["rs"]).groupby(["rs", "rent_time"]).size().rename("rentals")
        q = t.dropna(subset=["ts"]).groupby(["ts", "return_time"]).size().rename("returns")
        r.index.names = q.index.names = ["sno", "hour"]
        f = pd.concat([r, q], axis=1).fillna(0).astype(int).reset_index()
        flows.append(f)
        print(f"{ym}: {len(t)} trips in study area, {f.rentals.sum()} rentals, {f.returns.sum()} returns")
    if flows:
        f = pd.concat(flows, ignore_index=True)
        old = out / "flows_hourly.parquet"
        if old.exists():
            f = pd.concat([pd.read_parquet(old), f]).groupby(["sno", "hour"]).sum().reset_index()
        f.sort_values(["sno", "hour"]).to_parquet(old, index=False)
        print("flows_hourly rows", len(f))


def read_slots(repo, day):
    txt = subprocess.run(["git", "-C", str(repo), "cat-file", "-p", f"HEAD:data/slots/{day}.csv"],
                         capture_output=True, text=True)
    if txt.returncode != 0 or not txt.stdout:
        return None
    return pd.read_csv(io.StringIO(txt.stdout), dtype={"sno": str}, parse_dates=["infoTime"])


def cmd_snapshots(repo, out, start, end):
    st = pd.read_csv(out / "ntu_stations.csv", dtype={"sno": str})
    snos = set(st.sno)
    days = pd.date_range(start, end, freq="D")
    grid_all = pd.date_range(days[0], days[-1] + pd.Timedelta(days=1), freq="10min", inclusive="left")
    # collect raw records for study stations, then forward-fill on the common grid
    recs = []
    missing = []
    for d in days:
        s = read_slots(repo, d.strftime("%Y-%m-%d"))
        if s is None:
            missing.append(d.strftime("%Y-%m-%d")); continue
        s = s[s.sno.isin(snos)]
        recs.append(s)
    raw = pd.concat(recs, ignore_index=True).drop_duplicates(["sno", "infoTime"]).sort_values(["sno", "infoTime"])
    print(f"{len(raw)} snapshot records, {raw.sno.nunique()} stations, missing days: {missing}")
    frames = []
    for sno, g in raw.groupby("sno"):
        g = g.set_index("infoTime")[["available_rent_bikes", "available_return_bikes", "total"]]
        g = g[~g.index.duplicated()]
        v = g.reindex(g.index.union(grid_all)).sort_index().ffill().loc[grid_all]
        # how stale is each grid value (minutes since the station last reported)
        last = pd.Series(g.index, index=g.index).reindex(g.index.union(grid_all)).sort_index().ffill().loc[grid_all]
        age = ((grid_all - last.values) / pd.Timedelta(minutes=1)).astype(float)
        frames.append(pd.DataFrame({"sno": sno, "ts": grid_all, "bikes": v.available_rent_bikes.values,
                                    "docks": v.available_return_bikes.values, "total": v.total.values, "age_min": age}))
    panel = pd.concat(frames, ignore_index=True)
    # stations report only on change: a quiet night is not an outage, a quiet afternoon probably is
    hr = panel.ts.dt.hour
    stale = ((panel.age_min > 120) & (hr >= 7) & (hr < 23)) | (panel.age_min > 600)
    panel.loc[stale, ["bikes", "docks"]] = np.nan
    panel.to_parquet(out / "panel_10min.parquet", index=False)
    print("panel rows", len(panel), "nan share", round(panel.bikes.isna().mean(), 4))


def cmd_reconcile(out):
    panel = pd.read_parquet(out / "panel_10min.parquet")
    flows = pd.read_parquet(out / "flows_hourly.parquet")
    panel["hour"] = panel.ts.dt.floor("h")
    g = panel.groupby(["sno", "hour"])
    h = g.agg(stock0=("bikes", "first"), total=("total", "first"),
              exposure=("bikes", lambda x: float(np.mean(x > 0)) if x.notna().all() else np.nan),
              n=("bikes", "count")).reset_index()
    h["stock1"] = h.groupby("sno").stock0.shift(-1)
    h = h.merge(flows, on=["sno", "hour"], how="left").fillna({"rentals": 0, "returns": 0})
    h["delta"] = h.stock1 - h.stock0
    h["resid"] = h.delta - (h.returns - h.rentals)
    # 3-hour windows: a window whose summed residual is >= 5 bikes is an operator move
    h["win"] = h.hour.dt.floor("3h")
    w = h.groupby(["sno", "win"]).resid.sum().rename("win_resid").reset_index()
    h = h.merge(w, on=["sno", "win"], how="left")
    h["move"] = (h.win_resid.abs() >= 5).astype(int)
    h.to_parquet(out / "hourly.parquet", index=False)
    ok = h.dropna(subset=["delta"])
    quiet = ok[ok.move == 0]
    ss_res = ((quiet.delta - (quiet.returns - quiet.rentals)) ** 2).sum()
    ss_tot = ((quiet.delta - quiet.delta.mean()) ** 2).sum()
    print(f"station-hours {len(ok)}, move windows share {ok.move.mean():.3f}, "
          f"R2 of delta vs (returns-rentals) on quiet hours {1 - ss_res / ss_tot:.3f}")
    print("abs resid quantiles", ok.resid.abs().quantile([.5, .9, .99]).round(1).to_dict())
    mv = ok[ok.move == 1]
    print("implied truck bikes/day: drop-off", round(mv[mv.resid > 0].resid.sum() / ok.hour.dt.date.nunique(), 1),
          "pick-up", round(-mv[mv.resid < 0].resid.sum() / ok.hour.dt.date.nunique(), 1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "stations":
        out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
        cmd_stations(sys.argv[2], out)
    elif cmd == "trips":
        cmd_trips(Path(sys.argv[2]), Path(sys.argv[3]))
    elif cmd == "snapshots":
        cmd_snapshots(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4], sys.argv[5])
    elif cmd == "reconcile":
        cmd_reconcile(Path(sys.argv[2]))
