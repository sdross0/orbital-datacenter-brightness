"""
Reproduce the naked-eye satellite counts in the video.

Two brightness models, the same 500,000 satellites, the same observer, four
epochs after sunset. Only the brightness model changes between the columns.

    Model A   Boley, Lawler & Rein 2026 eq 2. Lambertian sphere, zeta = 160 m2.
              Their stated no-mitigation reference.
    Model B   Mallama et al. 2023 measured Gen2 Mini phase function in
              mitigation mode, offset +1.97 mag for the larger AI1 area.
              A floor, not a prediction. See README.

Requires numpy only.  python3 counts.py
"""

import numpy as np
import lsm as L

LAT = 37.23           # Blacksburg, Virginia
DEC = 0.0             # equinox
MLIM = 6.0            # naked eye limit
N_SATS = 500_000      # sun-synchronous half of the 1,000,000 filed cap
RELAX = 10.0          # deg RAAN spread, the paper's relaxed case

EPOCHS = ((18.00, "at sunset"),
          (18.50, "+30 min"),
          (19.00, "+60 min"),
          (19.50, "+90 min"))

SAMPLE_S = np.arange(0.0, 601.0, 60.0)     # 10 min of orbital phase


def count(cons, scale, lst, t_s, model):
    """Satellites above the horizon and brighter than MLIM, at time t_s."""
    r_obs, up, east, north = L.observer(LAT, lst)
    s = L.sun_dir(DEC)
    n = 0.0
    for c in cons:
        pos = L.propagate(c, t_s)
        if model == "boley":
            alt, az, d, V, lit = L.observe(pos, r_obs, up, east, north, s)
        else:
            alt, az, d, V, lit = L.observe_empirical(pos, r_obs, up, east, north, s)
        n += (lit & (alt > -0.005) & np.isfinite(V) & (V < MLIM)).sum() * scale
    return n


def main():
    cons = L.build_sso(N_SATS, relax_deg=RELAX)
    scale = N_SATS / L.total_of(cons)
    print("constellation  %d satellites, %d groups, %.1f deg RAAN spread"
          % (N_SATS, len(cons), RELAX))
    print("observer       lat %.2f, equinox, naked eye V < %.1f\n" % (LAT, MLIM))
    print("%-12s %22s %22s %8s" % ("epoch", "Boley no-mitigation",
                                   "Mallama-anchored", "ratio"))
    for lst, label in EPOCHS:
        el = L.sun_elevation(LAT, lst, DEC)
        a = np.array([count(cons, scale, lst, t, "boley") for t in SAMPLE_S])
        b = np.array([count(cons, scale, lst, t, "mini") for t in SAMPLE_S])
        ratio = "%.0fx" % (a.mean() / b.mean()) if b.mean() > 0.5 else "-"
        print("%-12s %10.0f [%5.0f-%5.0f] %10.0f [%5.0f-%5.0f] %8s"
              % (label, a.mean(), a.min(), a.max(),
                 b.mean(), b.min(), b.max(), ratio))
    print("\n(sun elevation: %s)"
          % ", ".join("%s %.1f deg" % (lab, L.sun_elevation(LAT, l, DEC))
                      for l, lab in EPOCHS))


if __name__ == "__main__":
    main()
