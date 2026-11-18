"""Walking and cycling minutes between stations, shared by the live page's tracker and the rider analysis.

docs/places.json (demo_places.py) holds path lengths from OpenStreetMap for the places and the stations around the
campus. Pairs it does not cover fall back to the straight line: x 1.25 at 80 m/min on foot, x 1.3 at 200 m/min by
bike, never less than one minute. The page (site/src/app.js) applies the same rule.
"""
import json
import math

import numpy as np

A64 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_"
WALK_M_PER_MIN, RIDE_M_PER_MIN = 80.0, 200.0


def straight_km(lat, lng):
    """Straight-line km between all pairs, with the page's flat-earth constants (111 km and 102.5 km per degree)."""
    return np.hypot(np.subtract.outer(lat, lat) * 111.0, np.subtract.outer(lng, lng) * 102.5)


def load_places(path):
    d = json.load(open(path, encoding="utf-8"))
    ids = [p["id"] for p in d["places"]] + list(d["stations"])
    walk = np.array([[A64.index(c) for c in row] for row in d["walk"]], float)
    ride = np.array([[A64.index(c) for c in row] for row in d["ride"]], float)
    return d, ids, walk, ride


def station_minutes(snos, lat, lng, places_path):
    """(KM, WALK, RIDE): straight-line km and minutes on foot and by bike between the stations in snos (N x N)."""
    km = straight_km(np.asarray(lat, float), np.asarray(lng, float))
    walk = np.maximum(1, np.round(km * 1.25 * 1000 / WALK_M_PER_MIN))
    ride = np.maximum(1, np.round(km * 1.3 * 1000 / RIDE_M_PER_MIN))
    try:
        _, ids, w, r = load_places(places_path)
    except (OSError, ValueError, KeyError):
        ids = []
    pos = {s: k for k, s in enumerate(ids)}
    here = [(i, pos[s]) for i, s in enumerate(snos) if s in pos]
    if here:
        a = np.array([i for i, _ in here]); b = np.array([k for _, k in here])
        walk[np.ix_(a, a)] = w[np.ix_(b, b)]; ride[np.ix_(a, a)] = r[np.ix_(b, b)]
    np.fill_diagonal(walk, 0); np.fill_diagonal(ride, 0)
    return km, walk.astype(int), ride.astype(int)


def place_minutes(snos, lat, lng, places_path):
    """For every place of places.json: minutes on foot to each station in snos, and to each other place.
    Returns (places, WALK_PS (P x N), WALK_PP (P x P))."""
    d, ids, w, _ = load_places(places_path)
    P = len(d["places"])
    pos = {s: k for k, s in enumerate(ids)}
    plat = np.array([p["lat"] for p in d["places"]]); plng = np.array([p["lng"] for p in d["places"]])
    km = np.hypot(np.subtract.outer(plat, np.asarray(lat, float)) * 111.0, np.subtract.outer(plng, np.asarray(lng, float)) * 102.5)
    ps = np.maximum(1, np.round(km * 1.25 * 1000 / WALK_M_PER_MIN))
    for j, s in enumerate(snos):
        if s in pos:
            ps[:, j] = w[:P, pos[s]]
    return d["places"], ps.astype(int), w[:P, :P].astype(int)
