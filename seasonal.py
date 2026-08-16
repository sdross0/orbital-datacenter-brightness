"""
How the evening peak moves through the year.

The tables elsewhere in this repository are all for an equinox. That turns out
to be close to the quietest time of year, so quoting it alone understates the
range badly. Run this to see the whole cycle.

The driver is phase angle. In a dawn-dusk sun-synchronous orbit the angle
Sun-satellite-observer depends on where the Sun sits relative to the orbit
plane, and that swings with the seasons. Near a solstice the satellites are
front-lit, at small phase angles, where Mallama's measured phase function is
several magnitudes brighter than at the side-lit angles you get near an
equinox. The idealised Lambertian model has a much weaker phase dependence, so
the mitigated case moves far more than the unmitigated one.

    python3 seasonal.py            # Blacksburg
    python3 seasonal.py 55         # any latitude
"""

import sys

import numpy as np

import lsm as L
import sky_view as SV
import solar

LAT = float(sys.argv[1]) if len(sys.argv) > 1 else 37.2
BORTLE = 1

DATES = [(2026, 1, 20, "Jan"), (2026, 2, 19, "Feb"), (2026, 3, 20, "Mar eq"),
         (2026, 4, 20, "Apr"), (2026, 5, 21, "May"), (2026, 6, 21, "Jun sol"),
         (2026, 7, 22, "Jul"), (2026, 8, 22, "Aug"), (2026, 9, 22, "Sep eq"),
         (2026, 10, 23, "Oct"), (2026, 11, 22, "Nov"), (2026, 12, 21, "Dec sol")]


def window(cons, scale, y, m, d, model):
    """First and last minute after sunset with at least one satellite up."""
    on = [t for t in range(0, 241, 2)
          if SV.whole_sky_count(cons, scale, y, m, d, LAT, t, True,
                                BORTLE, model) >= 1]
    return (on[0], on[-1]) if on else (None, None)


def main():
    cons = L.build_sso(500_000, relax_deg=10.0)
    scale = 500_000 / L.total_of(cons)

    print("Whole sky, %.1f N, dark site. Instantaneous counts at each peak.\n"
          % LAT)
    print("%-8s %11s %11s %8s %9s %9s"
          % ("date", "unmitigated", "mitigated", "stars", "mit/stars", "mit window"))

    for y, m, d, tag in DATES:
        dec, ra = solar.sun(y, m, d)
        ss = solar.sunset_lst(LAT, dec)
        if ss is None:
            print("%-8s  no sunset at this latitude" % tag)
            continue
        pk = {}
        for model in ("boley", "mini"):
            pk[model] = SV.peak_minutes(cons, scale, y, m, d, LAT, True,
                                        model, BORTLE)
        # Stars are counted at the mitigated peak, which is the moment the
        # comparison is about. Real catalogue positions for that date.
        t_star = pk["mini"][0] if pk["mini"][1] > 0 else pk["boley"][0]
        _, stars = SV.star_counts_zenith(LAT, dec, ra, ss, t_star, BORTLE)
        lo, hi = window(cons, scale, y, m, d, "mini")
        span = "none" if lo is None else "%d-%d min" % (lo, hi)
        ratio = pk["mini"][1] / stars if stars else 0.0
        print("%-8s %11s %11s %8s %9.2f %9s"
              % (tag, "{:,}".format(int(pk["boley"][1])),
                 "{:,}".format(int(pk["mini"][1])),
                 "{:,}".format(stars), ratio, span))

    print("\nThe mitigated column is the one to watch. It is the optimistic")
    print("reference case, and it is not a floor: at the December solstice it")
    print("is roughly ten times its equinox value.")


if __name__ == "__main__":
    main()
