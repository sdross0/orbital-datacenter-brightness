"""
How much does the sunset count move if every satellite is systematically
brighter or fainter than modeled?

The answer is very different for the two models, because of where each
population sits relative to the naked-eye threshold. Requires numpy.
"""

import numpy as np
import lsm as L

N_SATS, LAT, LST, DEC, MLIM = 500_000, 37.23, 18.00, 0.0, 6.0

cons = L.build_sso(N_SATS, relax_deg=10.0)
scale = N_SATS / L.total_of(cons)
r_obs, up, east, north = L.observer(LAT, LST)
s = L.sun_dir(DEC)

V = {}
for model in ("boley", "mini"):
    v = []
    for c in cons:
        p = L.propagate(c, 0.0)
        f = L.observe if model == "boley" else L.observe_empirical
        alt, az, d, Vv, lit = f(p, r_obs, up, east, north, s)
        v.append(Vv[lit & (alt > -0.005) & np.isfinite(Vv)])
    V[model] = np.concatenate(v)

print("Sunset count vs a systematic magnitude error, %s satellites" % f"{N_SATS:,}")
print("%18s %16s %14s" % ("systematic error", "no-mitigation", "mitigated"))
base = {}
for d in (-0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5, 1.0):
    row = []
    for m in ("boley", "mini"):
        n = (V[m] < MLIM - d).sum() * scale
        row.append(n)
        if d == 0.0:
            base[m] = n
    lab = "as modeled" if d == 0 else "%.1f mag %s" % (abs(d), "fainter" if d > 0 else "brighter")
    print("%18s %16.0f %14.0f" % (lab, row[0], row[1]))

print()
for m, lab in (("boley", "no-mitigation"), ("mini", "mitigated")):
    slope = ((V[m] < MLIM + 0.05).sum() - (V[m] < MLIM - 0.05).sum()) * scale
    print("%-16s %6.0f satellites per 0.1 mag = %5.1f%% of its count"
          % (lab, slope, 100 * slope / base[m]))
