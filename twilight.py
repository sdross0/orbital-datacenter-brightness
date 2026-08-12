"""
Twilight sky brightness and the naked-eye limiting magnitude that follows.

The counts elsewhere in this repository use a flat V < 6, which is a
DARK-SKY naked-eye threshold. Applying it at sunset credits the satellites
with a detection limit the sky does not allow. This module supplies the
epoch-dependent limit instead.

Two steps, both empirical approximations:

1. Zenith sky brightness vs solar elevation, mag/arcsec2. Piecewise fit by
   Han Kleijn (hnsky.org/sqm_twilight.htm) to SQM measurements combined
   with the Paranal / Crimean twilight photometry of Patat et al. (2006):

       0 to -12 deg   SQM = -1.057 x + 6.7489
     -12 to -18 deg   SQM = -0.0744 x^2 - 2.5768 x - 0.5845

   The two branches agree to 0.2 mag at the join, and the second reaches
   21.7 at -18 deg, the natural dark-sky value.

2. Naked-eye limiting magnitude for a point source vs sky brightness, the
   Schaefer relation as commonly implemented for SQM readings:

       NELM = 7.93 - 5 log10( 1 + 10^(4.316 - SQM/5) )

   This returns 6.5 at SQM 21.75, the conventional dark-sky limit.

CAVEATS, which are large:
  - Both are approximations, and naked-eye limits vary a lot between
    observers. Treat these as indicative, not precise.
  - Zenith only. During twilight the sky is much brighter toward the Sun,
    and the ring sits in that direction, so the true limit along the ring
    is worse than this. Using zenith is the generous choice.
  - No light pollution. This is a dark rural site.
"""

import numpy as np

SQM_DARK = 21.75


def sky_brightness(sun_el_deg):
    """Zenith sky brightness, mag/arcsec2, from solar elevation in degrees."""
    x = np.clip(np.asarray(sun_el_deg, dtype=float), -18.0, None)
    hi = -1.057 * x + 6.7489                       # 0 to -12
    lo = -0.0744 * x ** 2 - 2.5768 * x - 0.5845    # -12 to -18
    out = np.where(x > -12.0, hi, lo)
    return np.minimum(out, SQM_DARK)               # floor at the natural sky


def limiting_mag(sqm):
    """Naked-eye limiting magnitude for a point source (Schaefer relation)."""
    sqm = np.asarray(sqm, dtype=float)
    return 7.93 - 5.0 * np.log10(1.0 + 10.0 ** (4.316 - sqm / 5.0))


def add_glow(sqm_natural, sqm_artificial):
    """Combine two brightnesses given in mag/arcsec2, by adding in linear flux."""
    if sqm_artificial is None:
        return np.asarray(sqm_natural, dtype=float)
    a = 10.0 ** (-0.4 * np.asarray(sqm_natural, dtype=float))
    b = 10.0 ** (-0.4 * np.asarray(sqm_artificial, dtype=float))
    return -2.5 * np.log10(a + b)


# Representative artificial skyglow, mag/arcsec2, by Bortle class. Approximate.
BORTLE = {1: None, 2: 22.0, 3: 21.5, 4: 20.8, 5: 19.8, 6: 18.8, 7: 18.2, 8: 17.5}

# Kyba et al. 2023, Science 379, 265. Naked-eye limiting magnitude is falling
# at this rate globally, from a 9.6 %/yr rise in skyglow. Use with care: it is
# measured over 2011-2022 and extrapolating it for decades is speculative.
NELM_TREND_PER_YEAR = -0.044


def nelm(sun_el_deg, sqm_artificial=None):
    """Naked-eye limit at this solar elevation, optionally with skyglow."""
    return limiting_mag(add_glow(sky_brightness(sun_el_deg), sqm_artificial))


def nelm_bortle(sun_el_deg, bortle=1, years_ahead=0.0):
    """Same, for a Bortle class, optionally projected forward with Kyba."""
    return nelm(sun_el_deg, BORTLE[bortle]) + NELM_TREND_PER_YEAR * years_ahead


if __name__ == "__main__":
    print("Natural sky only:")
    print("%10s %12s %10s   %s" % ("sun el", "SQM", "naked eye", "stage"))
    for el, stage in ((0, "sunset"), (-3, ""), (-6, "civil twilight ends"),
                      (-9, ""), (-12, "nautical ends"), (-15, ""),
                      (-18, "astronomical ends"), (-24, "full dark")):
        print("%8.0f   %10.2f %10.2f   %s" % (el, sky_brightness(el), nelm(el), stage))
    print("\nWith artificial skyglow, 68 min after sunset (sun -13.5 deg):")
    print("%10s %12s %10s" % ("Bortle", "SQM", "naked eye"))
    for b in sorted(BORTLE):
        print("%10d   %10.2f %10.2f"
              % (b, add_glow(sky_brightness(-13.5), BORTLE[b]), nelm(-13.5, BORTLE[b])))
