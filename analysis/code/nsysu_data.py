"""Load the NSYSU logger output (data/kaohsiung/*.csv[.gz]) into a tidy 10-minute panel."""
import gzip
from pathlib import Path

import numpy as np
import pandas as pd

CAMPUS = {  # the eight on-campus stations (name contains 中山大學)
    "501209052": "Library", "501209070": "Xiziwan Hall", "501209051": "Engineering",
    "501209054": "Materials", "501209039": "Social Sci.", "501209069": "Gymnasium",
    "501209040": "Marine Eng.", "501209071": "Marine Res.",
}
GATEWAY = {  # off-campus stations students ride to after class (within ~1.2 km)
    "501209024": "Binhai/Linhai Rd.", "501209062": "Gushan ES (Dengshan)", "501209042": "Gushan ES (Linhai 2)",
    "501209036": "Pier-1 Bridge", "501209026": "KRT Sizihwan Exit 1", "501209023": "KRT Sizihwan Exit 2",
    "501209022": "Shaochuan/Anhai", "501209032": "Sizihwan Scenic", "501209025": "Gushan Marina Park",
    "501209104": "Shinhamacho", "501209028": "Xinbin Police",
}
# Taiwan public holidays inside the logging window (2026)
HOLIDAYS = {"2026-10-09", "2026-10-10"}


def load_logger(data_dir, days=None):
    """Return a DataFrame with columns date, slot (0..143), sno, bikes, docks (free docks), status, age."""
    data_dir = Path(data_dir)
    frames = []
    for p in sorted((data_dir / "kaohsiung").glob("*.csv*")):
        day = p.name.split(".")[0]
        if days is not None and day not in days:
            continue
        opener = gzip.open if p.suffix == ".gz" else open
        with opener(p, "rt", encoding="utf-8") as fh:
            df = pd.read_csv(fh, dtype={"sno": str})
        df["date"] = day
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    t = pd.to_timedelta(df["time"])
    # snap to the nearest 10-minute slot; the logger fires at hh:x0 but can lag by a minute or two
    df["slot"] = ((t.dt.total_seconds() + 300) // 600).astype(int) % 144
    df = df.sort_values(["date", "slot", "sno", "time"]).drop_duplicates(["date", "slot", "sno"], keep="last")
    df = df.drop(columns=["time"])
    df = df.rename(columns={"empty": "docks"})  # "empty" collides with DataFrame.empty
    df["bikes"] = pd.to_numeric(df["bikes"], errors="coerce")
    df["docks"] = pd.to_numeric(df["docks"], errors="coerce")
    df.loc[df["status"] != 1, ["bikes", "docks"]] = np.nan  # out of service is not a stockout
    df["dow"] = pd.to_datetime(df["date"]).dt.dayofweek
    df["weekday"] = (df["dow"] < 5) & ~df["date"].isin(HOLIDAYS)
    return df.reset_index(drop=True)


def load_stations(data_dir):
    st = pd.read_csv(Path(data_dir) / "stations.csv", dtype={"sno": str})
    st["group"] = np.where(st.sno.isin(CAMPUS), "campus", np.where(st.sno.isin(GATEWAY), "gateway", "other"))
    st["short"] = st.sno.map({**CAMPUS, **GATEWAY})
    return st


def panel(df, value="bikes"):
    """Wide table: index (date, slot), columns sno."""
    return df.pivot_table(index=["date", "slot"], columns="sno", values=value)
