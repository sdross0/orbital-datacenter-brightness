"""
How much does the assumed spread in orbital plane matter?

Almost everything else in this repository is built from numbers SpaceX filed.
The spread in right ascension of the ascending node is not one of them. SpaceX
filed a tolerance of +/- 30 degrees; this repository renders +/- 10, which is
the "relaxed" case in Boley et al. That choice was inherited rather than
derived, and it turns out to matter more than any other single assumption here
apart from the brightness model itself.

Two things this script exists to show.

**The spread interacts with the season.** A tight ring holds every satellite
near the terminator plane, so they all share roughly one phase-angle geometry,
and that geometry swings hard with the Sun's declination. A wide ring spreads
them over many phase angles at once, so some subset is always favourably lit
and the seasonal variation is damped. The large seasonal swing reported in
README.md is therefore partly a consequence of the 10 degree choice, and it is
substantially weaker at the filed 30 degrees.

**A single run is not a result.** The filed configuration has only about a
hundred orbital planes, and each one draws its node from the spread at random.
With that few draws the sampling itself moves the answer, by tens of percent
in the mitigated case. So this reports a mean and a spread over several seeds
rather than one number, and any single-seed figure quoted elsewhere in this
repository should be read with that scatter attached.

    python3 raan_sensitivity.py                 # equinox
    python3 raan_sensitivity.py --dec           # December solstice
    python3 raan_sensitivity.py --lat 55        # any latitude
    python3 raan_sensitivity.py --seeds 8       # bigger ensemble, slower
"""

import argparse

import numpy as np

import lsm as L
import sky_view as SV
import solar

BORTLE = 1
SPREADS = (5.0, 10.0, 20.0, 30.0)
NOTE = {10.0: "  <- used here (Boley 'relaxed')",
        30.0: "  <- SpaceX filed tolerance"}


def ensemble(y, m, d, lat, spread, seeds):
    """Peak whole-sky count for each model, over `seeds` plane realisations."""
    out = {"boley": [], "mini": []}
    for seed in range(1, seeds + 1):
        cons = L.build_sso(500_000, relax_deg=spread, seed=seed)
        scale = 500_000 / L.total_of(cons)
        for model in out:
            out[model].append(
                SV.peak_minutes(cons, scale, y, m, d, lat, True,
                                model, BORTLE)[1])
    return {k: np.array(v, float) for k, v in out.items()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, default=37.2)
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--dec", action="store_true",
                   help="December solstice instead of the September equinox")
    a = p.parse_args()

    y, m, d, tag = ((2026, 12, 21, "December solstice") if a.dec
                    else (2026, 9, 22, "September equinox"))
    dec, _ = solar.sun(y, m, d)
    if solar.sunset_lst(a.lat, dec) is None:
        print("No sunset at %.1f N on this date." % a.lat)
        return

    print("%s, whole sky, %.1f N, dark site." % (tag, a.lat))
    print("Each model at its own peak. Mean +/- sd over %d plane "
          "realisations.\n" % a.seeds)
    print("  %-14s %20s %18s" % ("RAAN spread", "unmitigated", "mitigated"))

    res = {}
    for s in SPREADS:
        r = ensemble(y, m, d, a.lat, s, a.seeds)
        res[s] = r
        print("  +/- %-10.0f %11s +/- %5s %10s +/- %5s%s"
              % (s,
                 "{:,}".format(int(round(r["boley"].mean()))),
                 "{:,}".format(int(round(r["boley"].std()))),
                 "{:,}".format(int(round(r["mini"].mean()))),
                 "{:,}".format(int(round(r["mini"].std()))),
                 NOTE.get(s, "")))

    print()
    for model, label in (("boley", "unmitigated"), ("mini", "mitigated")):
        mu = [res[s][model].mean() for s in SPREADS]
        lo, hi = min(mu), max(mu)
        print("  %-12s across the filed range: %.1fx"
              % (label, hi / lo if lo > 0 else float("inf")))
    print("\n  Scatter between realisations at the value used (+/- 10 deg) is")
    print("  %.0f%% of the mean for the mitigated case and %.0f%% for the"
          % (100 * res[10.0]["mini"].std() / res[10.0]["mini"].mean(),
             100 * res[10.0]["boley"].std() / res[10.0]["boley"].mean()))
    print("  unmitigated one. Quote the mitigated case to two significant")
    print("  figures at most.")


if __name__ == "__main__":
    main()
