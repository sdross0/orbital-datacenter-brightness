"""
Real star counts, and a synthetic sky drawn from them.

Cumulative counts brighter than visual magnitude m, whole sky, from the
standard tabulation (Yale Bright Star Catalogue / Allen's Astrophysical
Quantities). These are measured numbers, not a model.
"""

import numpy as np

# whole-sky cumulative counts N(< m)
MAG = np.array([-1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 6.5, 7.0, 8.0])
NCUM = np.array([2,     6,   15,  48, 171, 513, 1602, 4800, 9110, 14000, 42000],
                dtype=float)


def n_brighter(m, hemisphere=True):
    """Stars brighter than m. Half the sky is above the horizon."""
    n = np.interp(m, MAG, np.log10(np.maximum(NCUM, 1e-9)))
    n = 10 ** n
    return n / 2.0 if hemisphere else n


def sample_sky(m_limit=6.5, seed=17, hemisphere=True):
    """
    Draw stars with the observed magnitude distribution and a Milky Way
    concentration. Returns (alt, az, mag) for stars above the horizon.
    """
    rng = np.random.default_rng(seed)
    n_tot = int(n_brighter(m_limit, hemisphere))

    # invert the cumulative distribution to draw magnitudes
    grid = np.linspace(MAG[0], m_limit, 400)
    cum = 10 ** np.interp(grid, MAG, np.log10(NCUM))
    cum = cum / cum[-1]
    mag = np.interp(rng.random(n_tot), cum, grid)

    # positions: isotropic, plus a galactic-plane overdensity
    alt = np.arcsin(rng.random(n_tot))                  # uniform on hemisphere
    az = rng.random(n_tot) * 2 * np.pi
    # tilt a band across the sky and pull ~35% of stars toward it
    band = rng.random(n_tot) < 0.35
    nb = band.sum()
    t = rng.random(nb) * 2 * np.pi
    b_alt = np.radians(38) + np.radians(9) * rng.standard_normal(nb)
    b_az = t
    alt[band] = np.clip(b_alt, 0.02, np.pi / 2 - 0.02)
    az[band] = b_az
    return alt, az, mag
