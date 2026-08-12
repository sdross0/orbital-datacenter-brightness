"""
Twilight sky radiance over the whole dome.

`twilight.py` gives the ZENITH brightness against solar elevation, calibrated
to measurement. That is one number for the whole sky, which is not enough to
render a frame: during twilight the sky toward the Sun is several magnitudes
brighter than the zenith, and the anti-solar sky carries the rising shadow of
the Earth and the Belt of Venus above it.

This module spreads the measured zenith value over the dome:

    S(alt, theta) = S_zenith
                    - A exp(-theta / theta0)      brightening toward the Sun
                    - B (X(alt) - 1)              brightening toward the horizon
                    + shadow(alt, theta)          Earth's shadow, anti-solar

where theta is the angular distance from the Sun and X is airmass. S is in
mag/arcsec2, so a NEGATIVE term means brighter.

The shape parameters are empirical and chosen to look right; only the zenith
is anchored to data. That is a real limitation and it is why the counts in
this repository still quote the zenith value: the frame is the illustration,
the counts are the claim.

Colour is handled separately: twilight reddens toward the Sun and toward the
horizon, because the light has come through more air.
"""

import numpy as np
import twilight as T

DEG = np.pi / 180.0

A_SUN, THETA0 = 3.0, 28.0        # mag, deg. Brightening toward the Sun.
H_AIRGLOW = 90.0                 # km, emitting layer height                 # mag per unit airmass beyond 1
BELT_MAG = 0.55                  # Belt of Venus enhancement
SHADOW_MAG = 0.85                # darkening inside Earth's shadow


def airmass(alt_rad):
    """Kasten-Young, floored at 2 deg so it stays finite below the horizon."""
    z = np.clip(90.0 - np.maximum(alt_rad / DEG, 2.0), 0.0, 88.0)
    return 1.0 / (np.cos(z * DEG) + 0.50572 * (96.07995 - z) ** -1.6364)


def airglow(alt):
    """
    Brightening toward the horizon from the airglow layer, in magnitudes.

    Two competing effects. The van Rhijn factor is the extra path length
    through a shell at H_AIRGLOW, which brightens the sky toward the horizon.
    Extinction along that same path attenuates it. The product peaks around
    10-15 degrees elevation and falls again at the horizon, which is why a
    genuinely dark horizon can look darker than the sky above it.

    Returns a magnitude offset: negative is brighter.
    """
    RE = 6371.0
    z = np.pi / 2 - np.maximum(alt, 0.5 * DEG)
    q = (RE / (RE + H_AIRGLOW)) ** 2 * np.sin(z) ** 2
    van_rhijn = 1.0 / np.sqrt(np.maximum(1.0 - q, 1e-6))
    X = airmass(alt)
    ratio = van_rhijn * 10.0 ** (-0.4 * 0.15 * (X - 1.0))
    return -2.5 * np.log10(np.maximum(ratio, 1e-6))


def shadow_height(sun_alt_deg):
    """Approximate elevation of the top of Earth's shadow, anti-solar."""
    return np.clip(-2.1 * sun_alt_deg, 0.0, 90.0)


def brightness(alt, az, sun_alt_deg, sun_az_rad):
    """Sky brightness, mag/arcsec2, for arrays of altitude and azimuth (rad)."""
    S0 = float(T.sky_brightness(sun_alt_deg))
    sa = sun_alt_deg * DEG
    cos_t = (np.sin(alt) * np.sin(sa)
             + np.cos(alt) * np.cos(sa) * np.cos(az - sun_az_rad))
    theta = np.degrees(np.arccos(np.clip(cos_t, -1, 1)))

    # The directional glow is residual twilight: it fades as the Sun sinks and
    # is gone by the end of astronomical twilight.
    twi = np.clip((sun_alt_deg + 18.0) / 18.0, 0.0, 1.0)
    S = S0 - A_SUN * twi * np.exp(-theta / THETA0) + airglow(alt)

    # anti-solar: Earth's shadow below its top, Belt of Venus just above
    h = shadow_height(sun_alt_deg)
    anti = np.clip((theta - 90.0) / 60.0, 0.0, 1.0)          # 0 near Sun, 1 opposite
    e = alt / DEG
    inside = np.clip((h - e) / 4.0, 0.0, 1.0)
    belt = np.exp(-((e - h - 4.0) / 5.0) ** 2)
    S = S + anti * (SHADOW_MAG * inside - BELT_MAG * belt)
    return S, theta


def colour(theta, alt, sun_alt_deg):
    """RGB hue of the twilight sky. Warm toward the Sun and toward the horizon."""
    warm = np.exp(-theta / 46.0) * np.clip(1.0 - alt / (35 * DEG), 0.0, 1.0)
    h = shadow_height(sun_alt_deg)
    e = alt / DEG
    belt = np.exp(-((e - h - 4.0) / 6.0) ** 2) * np.clip((theta - 100.0) / 60.0, 0, 1)
    day = np.array([0.42, 0.55, 1.00])       # scattered blue
    dusk = np.array([1.00, 0.62, 0.34])      # sunset orange
    pink = np.array([1.00, 0.68, 0.72])      # Belt of Venus
    w = np.clip(warm, 0, 1)[..., None]
    b = np.clip(belt, 0, 1)[..., None]
    c = day * (1 - w) + dusk * w
    return c * (1 - b) + pink * b


def radiance(alt, az, sun_alt_deg, sun_az_rad, pix_arcsec2):
    """Linear sky flux per pixel, and its colour."""
    S, theta = brightness(alt, az, sun_alt_deg, sun_az_rad)
    m_pix = S - 2.5 * np.log10(pix_arcsec2)
    f = 10.0 ** (-0.4 * m_pix)
    return f, colour(theta, alt, sun_alt_deg), S
