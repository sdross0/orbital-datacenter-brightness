"""
Compose one ground frame: modelled twilight sky, real stars, satellites.

Everything is carried in linear flux per pixel, so a point source appears if
its flux beats the local sky. Visibility is a property of the image rather
than a separate threshold applied afterwards.
"""

import numpy as np
import lsm as L
import twilight as T
import skymodel as SK
import realstars as RS

DEG = np.pi / 180.0
W, H = 1672, 940
HFOV, AZ0, EL0 = 95.0, 315.0, 25.0
LAT = 37.23
RA_SUN = 12.0                      # September equinox
DEC = 0.0                          # solar declination, deg. 0 is an equinox.
SUNSET_LST = 18.0


def basis(az0_deg, el0_deg):
    a, e = az0_deg * DEG, el0_deg * DEG
    fwd = np.array([np.cos(e) * np.sin(a), np.cos(e) * np.cos(a), np.sin(e)])
    zen = np.array([0.0, 0.0, 1.0])
    right = np.cross(fwd, zen); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return fwd, right, up


FWD, RIGHT, UP = basis(AZ0, EL0)
FOC = (W / 2) / np.tan(HFOV * DEG / 2)
CX, CY = W / 2.0, H / 2.0
PIX_ARCSEC2 = (HFOV * 3600.0 / W) ** 2


def pixel_altaz():
    xx, yy = np.meshgrid(np.arange(W) - CX, CY - np.arange(H))
    d = (FOC * FWD[None, None, :] + xx[..., None] * RIGHT[None, None, :]
         + yy[..., None] * UP[None, None, :])
    d /= np.linalg.norm(d, axis=2, keepdims=True)
    alt = np.arcsin(np.clip(d[..., 2], -1, 1))
    az = np.arctan2(d[..., 0], d[..., 1]) % (2 * np.pi)
    return alt, az


def project(alt, az):
    d = np.stack([np.cos(alt) * np.sin(az), np.cos(alt) * np.cos(az), np.sin(alt)], -1)
    Z = d @ FWD
    x = CX + FOC * (d @ RIGHT) / np.where(Z == 0, 1e-9, Z)
    y = CY - FOC * (d @ UP) / np.where(Z == 0, 1e-9, Z)
    return x, y, Z > 0


def sun_altaz(mins):
    """Sun position at `mins` after sunset, from the same geometry as lsm."""
    lst = SUNSET_LST + mins / 60.0
    r_obs, up, east, north = L.observer(LAT, lst)
    s = L.sun_dir(DEC)
    return (np.degrees(np.arcsin(np.clip(s @ up, -1, 1))),
            np.arctan2(s @ east, s @ north) % (2 * np.pi))


def stamp(img, x, y, flux, rgb, sigma=1.15):
    """Add a Gaussian point source, in linear flux."""
    r = 4
    ix, iy = int(round(x)), int(round(y))
    if ix < -r or iy < -r or ix >= W + r or iy >= H + r:
        return
    x0, x1 = max(0, ix - r), min(W, ix + r + 1)
    y0, y1 = max(0, iy - r), min(H, iy + r + 1)
    if x1 <= x0 or y1 <= y0:
        return
    gx = np.arange(x0, x1) - x
    gy = np.arange(y0, y1) - y
    g = np.exp(-(gx[None, :] ** 2 + gy[:, None] ** 2) / (2 * sigma ** 2))
    g /= 2 * np.pi * sigma ** 2
    img[y0:y1, x0:x1] += (g * flux)[..., None] * rgb


def ground_mask(alt):
    """Simple ridge silhouette so the horizon is not a razor edge."""
    rng = np.random.default_rng(4)
    prof = np.cumsum(rng.normal(0, 1.0, W))
    prof = np.convolve(prof, np.ones(140) / 140, mode="same")
    prof = prof - prof.mean()
    prof = prof / (np.abs(prof).max() + 1e-9) * 1.6 * DEG
    return alt < prof[None, :]


def render(mins, model="boley", cons=None, scale=1.0, sat_gain=1.0,
           dt_sky=0.0, nsub=1):
    """
    dt_sky is the span of sky time this frame covers, in seconds. During the
    fast travel segments a single frame spans a minute or more, over which a
    satellite crosses tens of degrees, so it is sampled at `nsub` points and
    each gets 1/nsub of the flux. The result is what a real time-lapse shows:
    the ring smears into continuous bands while the sky darkens, then resolves
    back into separate points when the clock slows for a hold.
    """
    sun_el, sun_az = sun_altaz(mins)
    alt, az = pixel_altaz()

    fsky, csky, S = SK.radiance(alt, az, sun_el, sun_az, PIX_ARCSEC2)
    img = fsky[..., None] * csky

    lst = SUNSET_LST + mins / 60.0
    s_alt, s_az, s_mag, s_rgb = RS.sky(lst, RA_SUN, LAT)
    vis = s_alt > 0
    sx, sy, front = project(s_alt[vis], s_az[vis])
    mg, rgb = s_mag[vis], s_rgb[vis]
    ext = L.K_EXT * L.airmass(s_alt[vis])
    for i in np.nonzero(front & (sx > -6) & (sx < W + 6) & (sy > -6) & (sy < H + 6))[0]:
        stamp(img, sx[i], sy[i], 10.0 ** (-0.4 * (mg[i] + ext[i])), rgb[i])

    n_vis = 0
    if cons is not None:
        r_obs, up, east, north = L.observer(LAT, lst)
        sdir = L.sun_dir(DEC)
        offs = ([0.0] if nsub <= 1 else
                np.linspace(-dt_sky / 2, dt_sky / 2, nsub))
        for c in cons:
          for dt in offs:
            pos = L.propagate(c, dt)
            f = L.observe if model == "boley" else L.observe_empirical
            a, z, d, V, lit = f(pos, r_obs, up, east, north, sdir)
            # Keep only what an eye could actually detect, against the LOCAL
            # sky at that point, not the zenith. Below this a human sees
            # nothing, so drawing it would make the picture disagree with the
            # number beside it.
            S_loc, _ = SK.brightness(a, z, sun_el, sun_az)
            lim_loc = T.limiting_mag(S_loc)
            k = lit & np.isfinite(V) & (a > 0) & (V < lim_loc)
            if not k.any():
                continue
            xs, ys, fr = project(a[k], z[k])
            Vk = V[k]
            good = fr & (xs > -6) & (xs < W + 6) & (ys > -6) & (ys < H + 6)
            fl = 10.0 ** (-0.4 * Vk) * scale * sat_gain / max(len(offs), 1)
            wht = np.array([0.95, 0.97, 1.0])
            for i in np.nonzero(good)[0]:
                stamp(img, xs[i], ys[i], fl[i], wht, sigma=1.0)
            n_vis += good.sum() * scale / max(len(offs), 1)

    gm = ground_mask(alt)
    img[gm] = img[gm].mean(axis=1, keepdims=True) * 0.018 * np.array([1.0, 0.94, 0.86])
    return img, sun_el, S, n_vis


def tonemap(img, S_zenith):
    """
    Partial eye adaptation plus a compressive highlight roll-off.

    The western horizon during twilight is genuinely a hundred times brighter
    than the zenith, so a linear map clips it to white and destroys the
    gradient. The Reinhard curve keeps that structure while still letting the
    early frames read as much brighter than the late ones.
    """
    ref = 10.0 ** (-0.4 * (21.7 - 2.5 * np.log10(PIX_ARCSEC2)))
    cur = 10.0 ** (-0.4 * (S_zenith - 2.5 * np.log10(PIX_ARCSEC2)))
    scale = 0.028 / ref * (ref / cur) ** 0.72
    x = img * scale
    return (x / (1.0 + x)) ** (1 / 2.2)
