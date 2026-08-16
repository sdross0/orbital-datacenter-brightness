"""
Where the Sun is, for a real date.

Low-precision solar position, good to about 0.01 degrees, which is far finer
than anything else in this model needs. Standard formulation.

Returns what the rest of the code wants: declination (which sets the geometry),
right ascension (which sets the star field), and the local solar time of sunset
or sunrise at a given latitude.
"""

import numpy as np

DEG = np.pi / 180.0
OBLIQ = 23.439


def _days_since_j2000(year, month, day):
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = (day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045)
    return jdn - 2451545.0 + 0.5


def sun(year, month, day):
    """Solar declination in degrees and right ascension in hours."""
    d = _days_since_j2000(year, month, day)
    Lm = (280.460 + 0.9856474 * d) % 360.0            # mean longitude
    g = ((357.528 + 0.9856003 * d) % 360.0) * DEG     # mean anomaly
    lam = (Lm + 1.915 * np.sin(g) + 0.020 * np.sin(2 * g)) * DEG
    e = OBLIQ * DEG
    dec = np.degrees(np.arcsin(np.sin(e) * np.sin(lam)))
    ra = np.degrees(np.arctan2(np.cos(e) * np.sin(lam), np.cos(lam))) % 360.0
    return dec, ra / 15.0


def sunset_lst(lat_deg, dec_deg):
    """Local solar time of sunset, hours. None if the Sun does not set."""
    x = -np.tan(lat_deg * DEG) * np.tan(dec_deg * DEG)
    if x < -1:
        return None                                    # midnight sun
    if x > 1:
        return None                                    # polar night
    return 12.0 + np.degrees(np.arccos(x)) / 15.0


def sunrise_lst(lat_deg, dec_deg):
    ss = sunset_lst(lat_deg, dec_deg)
    return None if ss is None else 24.0 - ss


if __name__ == "__main__":
    for y, m, d, lab in ((2026, 3, 20, "Mar equinox"), (2026, 6, 21, "Jun solstice"),
                         (2026, 9, 22, "Sep equinox"), (2026, 12, 21, "Dec solstice")):
        dec, ra = sun(y, m, d)
        ss = sunset_lst(37.23, dec)
        print("%-14s dec %+6.2f deg   RA %5.2f h   sunset %5.2f local solar"
              % (lab, dec, ra, ss))
