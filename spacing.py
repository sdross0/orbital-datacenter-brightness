"""
Satellite-to-satellite spacing in the filed sun-synchronous groups.

Three different questions get three different answers, so all three are
computed here:

  1. in-plane spacing      along-track gap between neighbours in one plane
  2. nearest neighbour     true 3D distance to the closest other satellite
  3. angular spacing       how far apart they look from the ground

Requires numpy. scipy is optional and only used for (2).
"""

import numpy as np
import lsm as L

N_SATS = 500_000
LAT, LST, DEC = 37.23, 18.00, 0.0
MLIM = 6.0

cons = L.build_sso(N_SATS, relax_deg=10.0)
scale = N_SATS / L.total_of(cons)

# ---------------------------------------------------------------- 1. in-plane
# Satellites in a plane are evenly spread in true anomaly, so the along-track
# gap is just the orbit circumference divided by the number in that plane.
print("1. IN-PLANE (along-track) SPACING")
print("   %-22s %7s %7s %9s %12s" % ("group", "planes", "per pl", "circum km", "spacing km"))
tot = 0
for i, c in enumerate(cons):
    a = c["a"]
    n_planes, per_plane = c["th0"].shape
    circ = 2 * np.pi * a.mean()
    tot += c["total"]
    print("   %-22s %7d %7d %9.0f %12.1f"
          % ("%.0f-%.0f km" % (a.min() - L.R_E, a.max() - L.R_E),
             n_planes, per_plane, circ, circ / per_plane))
print("   total satellites: %d" % tot)

# ------------------------------------------------------------ 2. nearest nbr
# The real minimum separation, which also picks up satellites in adjacent
# planes and at the points where the two node families cross.
pos = np.vstack([L.propagate(c, 0.0) for c in cons])
print("\n2. NEAREST NEIGHBOUR IN 3D  (n = %d)" % len(pos))
try:
    from scipy.spatial import cKDTree
    d, _ = cKDTree(pos).query(pos, k=2)
    nn = d[:, 1]
    print("   median %.1f km   mean %.1f km" % (np.median(nn), nn.mean()))
    print("   5th pct %.1f km   95th pct %.1f km   min %.2f km"
          % (np.percentile(nn, 5), np.percentile(nn, 95), nn.min()))
except ImportError:
    print("   scipy not installed, skipping")

# -------------------------------------------------------------- 3. angular
# Visible satellites spread over a hemisphere. Mean spacing is the inverse
# square root of the areal density.
HEMI = 2 * np.pi * (180 / np.pi) ** 2          # 20,626 square degrees
r_obs, up, east, north = L.observer(LAT, LST)
s = L.sun_dir(DEC)
print("\n3. ANGULAR SPACING AS SEEN FROM THE GROUND, AT SUNSET")
print("   hemisphere = %.0f square degrees, full Moon = 0.52 deg across" % HEMI)
for model, lab in (("boley", "Boley"), ("mini", "Mallama")):
    n = 0.0
    for c in cons:
        p = L.propagate(c, 0.0)
        f = L.observe if model == "boley" else L.observe_empirical
        alt, az, d_, V, lit = f(p, r_obs, up, east, north, s)
        n += (lit & (alt > -0.005) & np.isfinite(V) & (V < MLIM)).sum() * scale
    dens = n / HEMI
    print("   %-8s %7.0f visible   %.2f per sq deg   mean separation %.2f deg"
          % (lab, n, dens, 1 / np.sqrt(dens)))

# The more intuitive number: two neighbours in the same train, which is the
# 10 km along-track gap divided by the slant range. Shrinks toward the horizon.
print("\n4. APPARENT GAP BETWEEN TWO NEIGHBOURS IN ONE TRAIN")
h, gap = 750.0, 10.0
print("   (%.0f km along-track gap, %.0f km altitude)" % (gap, h))
print("   %10s %10s %14s" % ("elevation", "range km", "separation"))
for e in (90, 60, 45, 30, 20, 10, 5, 0):
    se = np.sin(np.radians(e))
    d = np.sqrt((L.R_E * se) ** 2 + 2 * L.R_E * h + h * h) - L.R_E * se
    print("   %8.0f deg %10.0f %11.2f deg" % (e, d, np.degrees(gap / d)))
