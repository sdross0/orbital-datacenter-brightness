"""
Counts using an epoch-dependent naked-eye limit instead of a flat V < 6.

A flat V < 6 is a dark-sky threshold. Applied at sunset it credits the
satellites with a detection limit the twilight sky does not allow, so this
script sets the limit from the solar elevation at each step (twilight.py)
and counts stars against the same limit.

It also reports counts under the reporting conventions of Boley, Lawler &
Rein 2026, which are stricter than the ones used in counts.py:

    - satellites only above 10 degrees elevation, not merely above the horizon
    - V < 5 rather than V < 6
    - counts only shown once the Sun is 6 degrees or more below the horizon

Stars are counted from the real HYG catalogue at the actual date and
latitude, not from the isotropic synthetic sky in stars.py. The synthetic
sky assumes stars are spread evenly over the hemisphere, which overcounts
what is actually above the horizon from Blacksburg at the equinox by about
ten percent. Only the star column is affected.

Requires numpy. See twilight.py for the caveats, which are substantial. In
particular the sky brightness is for the ZENITH.

    python3 counts_twilight.py            natural sky, dark site
    python3 counts_twilight.py 4          Bortle 4 skyglow
"""

import sys
import numpy as np
import lsm as L
import twilight as T
import realstars as RS

N_SATS, LAT, DEC = 500_000, 37.23, 0.0
RA_SUN = 12.0                        # September equinox, hours
STEP_HR, N_STEP = 0.125, 25          # 7.5 minute steps, out to 3 hours
ALT_MIN = np.radians(10.0)           # Boley et al. elevation cut
V_BOLEY = 5.0                        # Boley et al. magnitude cut
SUN_GATE = -6.0                      # they show counts only below this


def main(bortle=1):
    sqm_art = T.BORTLE[bortle]
    cons = L.build_sso(N_SATS, relax_deg=10.0)
    scale = N_SATS / L.total_of(cons)
    s = L.sun_dir(DEC)

    print("Blacksburg, equinox. %s satellites. Bortle %d%s."
          % (f"{N_SATS:,}", bortle, "" if sqm_art is None else
             ", skyglow %.1f mag/arcsec2" % sqm_art))
    print("'this work' = above the horizon, V < epoch limit.")
    print("'Boley conv' = above 10 deg, V < 5, shown only once the Sun is 6 deg down.\n")
    print("%6s %7s %7s %7s | %9s %9s %7s | %9s %9s"
          % ("min", "sun el", "SQM", "V lim", "unmit", "mitig", "stars",
             "unmit_B", "mitig_B"))

    peak = (0.0, -1.0, 0.0)
    for k in range(N_STEP):
        lst = 18.0 + k * STEP_HR
        el = L.sun_elevation(LAT, lst, DEC)
        sqm = float(T.add_glow(T.sky_brightness(el), sqm_art))
        vlim = float(T.nelm(el, sqm_art))
        r_obs, up, east, north = L.observer(LAT, lst)
        s_alt, s_az, s_mag, _ = RS.sky(lst, RA_SUN, LAT)
        up_now = s_alt > 0
        V_star = s_mag[up_now] + L.K_EXT * L.airmass(s_alt[up_now])
        ns = int((V_star < vlim).sum())
        res = {}
        for model in ("boley", "mini"):
            a = b = 0.0
            for c in cons:
                pos = L.propagate(c, 0.0)
                f = L.observe if model == "boley" else L.observe_empirical
                alt, az, d, V, lit = f(pos, r_obs, up, east, north, s)
                ok = lit & np.isfinite(V)
                a += (ok & (alt > -0.005) & (V < vlim)).sum() * scale
                b += (ok & (alt > ALT_MIN) & (V < V_BOLEY)).sum() * scale
            res[model] = (a, b)
        mins = (lst - 18.0) * 60.0
        if res["boley"][0] > peak[1]:
            peak = (mins, res["boley"][0], el)
        gated = el <= SUN_GATE
        print("%6.0f %7.1f %7.2f %7.2f | %9.0f %9.0f %7d | %9s %9s"
              % (mins, el, sqm, vlim, res["boley"][0], res["mini"][0], ns,
                 "%.0f" % res["boley"][1] if gated else "-",
                 "%.0f" % res["mini"][1] if gated else "-"))

    print("\nunmitigated peaks %.0f min after sunset (sun %.1f deg): %.0f satellites"
          % (peak[0], peak[2], peak[1]))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
