"""Route-search planner for the replay simulator (proposal Sec. 2.6).

Values: the birth-death chain of Sec. 2.4.1 (censoring-corrected rental and return rates, 10-minute steps,
no absorbing state) gives, for every station, the expected number of unmet rentals between now and the
end of the horizon H as a function of the stock. A backward pass gives V_a(s), the expected unmet rentals
from step a to H when the stock is s at step a; a forward pass from the current stock gives P_a(s), the
distribution of the stock at step a. The value of changing the stock of station i by d bikes when a truck
arrives in step a is

    B[i, a, d] = sum_s P_a(s) * (V_a(s) - V_a(clip(s + d, 0, c_i)))

(positive for useful drop-offs, negative for pick-ups, which cost the source its own future rentals).

Routes: a route is a sequence of up to M stations. For a fixed sequence the loads are chosen exactly by
dynamic programming over the truck load (0..Q), so the objective of a sequence is

    J = max over loads of sum_l B[i_l, a_l, d_l] - beta * route minutes.

Sequences are built by greedy insertion from a pool of candidate drop-off and pick-up stations, improved by
simulated annealing (insert / remove / swap / replace / segment reversal) and finished with 2-opt.
"""
import math

import numpy as np
from scipy.stats import poisson

STEP = 10                 # minutes per chain step


def kernels(lam_r, lam_q, cap, C):
    """One-step transition matrices K (N, C+1, C+1) and expected unmet rentals per step u (N, C+1).
    Rentals ~ Poisson(lam_r / 6) censored at the stock, returns ~ Poisson(lam_q / 6) censored at the free docks.
    States above a station's capacity are never reached; their rows are identity."""
    N = len(cap)
    K = np.zeros((N, C + 1, C + 1), dtype=np.float32)
    u = np.zeros((N, C + 1), dtype=np.float32)
    for n in range(N):
        c = int(cap[n])
        a, b = lam_r[n] * STEP / 60, lam_q[n] * STEP / 60
        M = int(max(a, b) + 8 * math.sqrt(max(a, b)) + 20) + c
        r = np.arange(M + 1)
        pr, pq = poisson.pmf(r, a), poisson.pmf(r, b)
        for i in range(c + 1):
            prc = pr[:i + 1].copy(); prc[i] = pr[i:].sum()                 # min(rentals, i)
            pqc = pq[:c - i + 1].copy(); pqc[c - i] = pq[c - i:].sum()     # min(returns, c - i)
            K[n, i, :c + 1] = np.convolve(pqc, prc[::-1])                  # index = i + returns - rentals
            u[n, i] = ((r[i + 1:] - i) * pr[i + 1:]).sum()                 # E[max(0, rentals - i)]
        for i in range(c + 1, C + 1):
            K[n, i, i] = 1.0
    return K, u


class ChainValues:
    """Expected-unmet value tables for one day type. rates_r, rates_q: (N, 24) hourly rates."""

    def __init__(self, rates_r, rates_q, cap, horizon_min, Q):
        self.cap = np.asarray(cap, int)
        self.N, self.C, self.Q = len(cap), int(self.cap.max()), Q
        self.A = horizon_min // STEP
        self.K, self.u = {}, {}
        for hod in range(24):
            self.K[hod], self.u[hod] = kernels(rates_r[:, hod], rates_q[:, hod], self.cap, self.C)
        s = np.arange(self.C + 1)[None, :, None]
        d = np.arange(-Q, Q + 1)[None, None, :]
        self.idx = np.clip(s + d, 0, self.cap[:, None, None]).reshape(self.N, -1)   # V[n, clip(s + d)]

    def benefit(self, t_min, bikes):
        """B (N, A, 2Q+1): unmet rentals avoided in [t, t + H) if the stock changes by d at step a."""
        A, N, C, Q = self.A, self.N, self.C, self.Q
        hods = [int((t_min + STEP * a) // 60) % 24 for a in range(A)]
        V = [None] * (A + 1)
        V[A] = np.zeros((N, C + 1), np.float32)
        for a in range(A - 1, -1, -1):
            V[a] = self.u[hods[a]] + np.einsum("nij,nj->ni", self.K[hods[a]], V[a + 1])
        P = np.zeros((N, C + 1), np.float32)
        P[np.arange(N), np.clip(bikes, 0, self.cap)] = 1.0
        B = np.empty((N, A, 2 * Q + 1), np.float32)
        for a in range(A):
            ev = (P * V[a]).sum(1)
            G = np.take_along_axis(V[a], self.idx, axis=1).reshape(N, C + 1, 2 * Q + 1)
            B[:, a, :] = ev[:, None] - np.einsum("ns,nsd->nd", P, G)
            P = np.einsum("ni,nij->nj", P, self.K[hods[a]])
        return B


class RoutePlanner:
    def __init__(self, travel_min, Q, stop_min, handle_min, horizon_min, beta=0.0, max_stops=6, iters=400,
                 n_drop=12, n_pick=12, depot_min=5.0, anneal=True):
        self.T = travel_min; self.Q = Q; self.stop = stop_min + handle_min
        self.A = horizon_min // STEP; self.beta = beta; self.M = max_stops; self.iters = iters
        self.n_drop, self.n_pick, self.depot = n_drop, n_pick, depot_min
        self.anneal = anneal
        self.stats = {"plans": 0, "searched": 0, "improved": 0, "v_greedy": 0.0, "v_final": 0.0}
        self.IDX = np.subtract.outer(np.arange(Q + 1), np.arange(Q + 1)) + Q       # [load, load'] -> d + Q

    # ---------------------------------------------------------------- evaluation of one sequence
    def _travel(self, a, b):
        return self.depot if a is None else self.T[a, b]

    def evaluate(self, route, back=False):
        t, prev = 0.0, self.pos
        f = np.full(self.Q + 1, -np.inf); f[self.load0] = 0.0
        args, times = [], []
        for s in route:
            t += self._travel(prev, s)
            a = int(t // STEP)
            if a >= self.A:
                return (-1e9, None) if back else -1e9
            M = f[:, None] + self.Bm[s][a][self.IDX]
            if back:
                args.append(M.argmax(0)); times.append(t)
            f = M.max(0)
            t += self.stop
            prev = s
        v = float(f.max()) - self.beta * t if route else 0.0
        if not back:
            return v
        loads, cur = [], int(f.argmax())
        for am in reversed(args):
            p = int(am[cur]); loads.append(p - cur); cur = p
        return v, list(zip(route, loads[::-1], times))

    # ---------------------------------------------------------------- search
    def plan(self, B, bikes, cap, pos, load0, claimed, rng):
        """Returns [(station, d, arrival offset in min)], d > 0 drop-off, d < 0 pick-up; [] if nothing pays."""
        Q = self.Q
        self.pos, self.load0 = pos, int(load0)
        t0 = np.full(len(bikes), self.depot) if pos is None else self.T[pos]
        a0 = np.minimum((t0 // STEP).astype(int), self.A - 1)
        ok = ~claimed
        dmax = np.minimum(Q, cap - bikes)
        pmax = np.minimum(Q, bikes)
        Bi0 = B[np.arange(len(bikes)), a0]                                   # (N, 2Q+1) at direct arrival
        drop_gain = np.where(np.arange(-Q, Q + 1)[None, :] <= dmax[:, None], Bi0, -np.inf)[:, Q + 1:].max(1)
        drop = np.where(ok & (dmax >= 1) & (drop_gain > 0.05))[0]
        drop = drop[np.argsort(-drop_gain[drop])][: self.n_drop]
        k = np.minimum(10, pmax)
        pick_loss = Bi0[np.arange(len(bikes)), Q - k] / np.maximum(k, 1)     # per bike, <= 0
        pick = np.where(ok & (pmax >= 3))[0]
        pick = pick[np.argsort(-pick_loss[pick])][: self.n_pick]
        pool = [int(x) for x in dict.fromkeys(list(drop) + (list(pick) if self.load0 < Q else []))]
        if len(drop) == 0:
            return []
        # value vectors with infeasible changes masked, per pool station and arrival step
        d = np.arange(-Q, Q + 1)
        self.Bm = {}
        for s in pool:
            m = (d >= -pmax[s]) & (d <= dmax[s])
            self.Bm[s] = np.where(m[None, :], B[s], -np.inf)
        # start: an empty truck needs a pick-up before any drop-off pays, so seed with the best (pick, drop) pair
        route, v = [], 0.0
        if self.load0 < 3:
            best = None
            for p_ in pick:
                for d_ in drop:
                    if p_ != d_:
                        w = self.evaluate([int(p_), int(d_)])
                        if best is None or w > best[0]:
                            best = (w, [int(p_), int(d_)])
            if best is None or best[0] <= 0:
                return []
            v, route = best
        # greedy insertion
        while len(route) < self.M:
            best = None
            for s in pool:
                if s in route:
                    continue
                for p in range(len(route) + 1):
                    r = route[:p] + [s] + route[p:]
                    w = self.evaluate(r)
                    if w > v + 1e-6 and (best is None or w > best[0]):
                        best = (w, r)
            if best is None:
                break
            v, route = best
        self.stats["plans"] += 1
        if self.anneal and self.iters > 0 and pool:
            v0 = v
            route, v = self._anneal(route, v, pool, rng)
            route, v = self._two_opt(route, v)
            self.stats["searched"] += 1
            self.stats["improved"] += int(v > v0 + 1e-6)
            self.stats["v_greedy"] += v0; self.stats["v_final"] += v
        if v <= 0 or not route:
            return []
        v, stops = self.evaluate(route, back=True)
        return [(int(s), int(dd), float(t)) for s, dd, t in stops if dd != 0]

    def _anneal(self, route, v, pool, rng, T0=0.5, T1=0.01):
        cur, vcur = list(route), v
        best, vbest = list(route), v
        for it in range(self.iters):
            T = T0 * (T1 / T0) ** (it / self.iters)
            r = list(cur)
            mv = rng.integers(5)
            out = [s for s in pool if s not in r]
            if mv == 0 and len(r) < self.M and out:                      # insert
                r.insert(int(rng.integers(len(r) + 1)), out[int(rng.integers(len(out)))])
            elif mv == 1 and len(r) > 1:                                 # remove
                r.pop(int(rng.integers(len(r))))
            elif mv == 2 and len(r) > 1:                                 # swap
                i, j = rng.choice(len(r), 2, replace=False); r[i], r[j] = r[j], r[i]
            elif mv == 3 and len(r) > 2:                                 # reverse a segment (2-opt move)
                i, j = sorted(rng.choice(len(r), 2, replace=False)); r[i:j + 1] = r[i:j + 1][::-1]
            elif mv == 4 and r and out:                                  # replace
                r[int(rng.integers(len(r)))] = out[int(rng.integers(len(out)))]
            else:
                continue
            w = self.evaluate(r)
            if w >= vcur or rng.random() < math.exp((w - vcur) / T):
                cur, vcur = r, w
                if w > vbest + 1e-9:
                    best, vbest = list(r), w
        return best, vbest

    def _two_opt(self, route, v):
        improved = True
        while improved and len(route) > 2:
            improved = False
            for i in range(len(route) - 1):
                for j in range(i + 1, len(route)):
                    r = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
                    w = self.evaluate(r)
                    if w > v + 1e-6:
                        route, v, improved = r, w, True
        return route, v
