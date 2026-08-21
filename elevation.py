"""
How high in the sky are they? Distribution of elevation angle.

The most common objection to these results is that a sun-synchronous ring is
seen edge-on from the ground, so the satellites hug the horizon and never
trouble the sky overhead. The first half of that is right and the second half
is not, and the difference is worth a table rather than an argument.

They do pile up low: at an equinox the median visible satellite sits about
15 degrees above the horizon. But the distribution has a long tail, a sixth of
them are more than 30 degrees up, and near the December solstice the ring
reaches the zenith.

Note also that the better the mitigation, the HIGHER the survivors sit. A
faint satellite only clears the naked-eye threshold when it is close, and
close means overhead: range and atmospheric extinction both punish the low
ones. So the optimistic column is an almost entirely high-sky population,
which is the opposite of what the edge-on-ring intuition predicts.

Same convention as the tables in README.md: whole sky, dark site, each model
at its own peak, zenith limiting magnitude.

    python3 elevation.py                # equinox and December solstice
    python3 elevation.py --lat 55
"""

import argparse

import numpy as np

import lsm as L
import sky_view as SV
import solar
import twilight as T

BORTLE = 1
CUTS = (10, 20, 30, 45, 60)
DATES = [(2026, 9, 22, "September equinox"), (2026, 12, 21, "December solstice")]


def elevations(cons, scale, y, m, d, lat, mins, model):
    """Elevation in degrees of every satellite over the naked-eye limit."""
    dec, _ = solar.sun(y, m, d)
    ss = solar.sunset_lst(lat, dec)
    lst = ss + mins / 60.0
    el = L.sun_elevation(lat, lst, dec)
    vl = float(T.nelm(el, SV.BORTLE_SQM[BORTLE]))
    r, u, e, n = L.observer(lat, lst)
    s = L.sun_dir(dec)
    f = L.observe if model == "boley" else L.observe_empirical
    out = []
    for c in cons:
        p = L.propagate(c, 0.0)
        a, z, dd, V, lit = f(p, r, u, e, n, s)
        k = lit & np.isfinite(V) & (a > 0) & (V < vl)
        out.append(np.degrees(a[k]))
    return np.concatenate(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, default=37.2)
    a = p.parse_args()

    cons = L.build_sso(500_000, relax_deg=10.0)
    scale = 500_000 / L.total_of(cons)
    print("Whole sky, %.1f N, dark site, each model at its own peak.\n" % a.lat)

    for y, m, d, tag in DATES:
        dec, _ = solar.sun(y, m, d)
        if solar.sunset_lst(a.lat, dec) is None:
            print("%s: no sunset at this latitude\n" % tag)
            continue
        print(tag)
        for model, label in (("boley", "no mitigation"), ("mini", "optimistic")):
            mins, total = SV.peak_minutes(cons, scale, y, m, d, a.lat,
                                          True, model, BORTLE)
            ev = elevations(cons, scale, y, m, d, a.lat, mins, model)
            if len(ev) == 0:
                print("  %-15s none visible at any epoch" % label)
                continue
            print("  %-15s %s visible, peak at %d min after sunset"
                  % (label, "{:,}".format(int(round(total))), mins))
            print("      median %.1f deg   p90 %.1f deg   highest %.1f deg"
                  % (np.median(ev), np.percentile(ev, 90), ev.max()))
            for c in CUTS:
                frac = (ev > c).mean()
                print("      above %2d deg: %5.1f%%   (%s)"
                      % (c, 100 * frac,
                         "{:,}".format(int(round(frac * total)))))
        print()


if __name__ == "__main__":
    main()
