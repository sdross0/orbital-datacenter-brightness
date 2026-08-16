"""
The whole sky as one cylindrical panorama, for a viewer that pans in a browser.

frame.py renders a gnomonic view: correct perspective, but fixed, and every
change of heading costs another render. That is fine for a video and wrong for
something a person drags around. Here the entire dome is rendered once in
altitude and azimuth, and the browser cuts a perspective window out of it at
whatever heading the user points, sixty times a second and with no server in
the loop.

Two differences from frame.py, both deliberate:

  - Point sources are stamped in one vectorized pass rather than a Python loop.
    At fifteen thousand satellites the loop costs a quarter of a second, which
    is the whole budget for an animation frame. The profile is identical.
  - The sky is drawn as a surface brightness map, with one pixel scale for the
    whole frame, so a patch of a given brightness is the same shade wherever it
    sits. The varying solid angle per pixel is dealt with where it matters, in
    the width of the point sources: this projection stretches azimuth by
    1/cos(alt), so a source is drawn as an ellipse of exactly that eccentricity
    and comes out round again once the viewer undoes the stretch.

The projection is equirectangular: x is azimuth, y is altitude, both linear.
It is not what an eye sees, and it is not meant to be. It is a storage format.
The perspective is restored in the viewer.
"""

import numpy as np

import lsm as L
import twilight as T
import skymodel as SK
import realstars as RS

DEG = np.pi / 180.0


# ------------------------------------------------------------------ stamping

def stamp_points(img, xs, ys, flux, rgb, alt, sigma=1.0, wrap_x=True):
    """
    Stamp sources whose horizontal width varies with altitude.

    Near the zenith the projection stretches azimuth without bound, so a source
    up there needs a very wide kernel and one down at the horizon does not.
    Using the widest kernel for all of them would cost a hundred times more
    than it needs to, so the sources are grouped into a few bands and each band
    gets a window sized to its own widest member.
    """
    st = x_stretch(alt)
    edges = [0.0, 1.5, 3.0, 6.0, 12.0, 1e9]
    for lo, hi in zip(edges[:-1], edges[1:]):
        k = (st >= lo) & (st < hi)
        if not k.any():
            continue
        sub = rgb if np.ndim(rgb) == 1 else rgb[k]
        stamp_many(img, xs[k], ys[k], flux[k], sub, sigma=sigma,
                   sigma_x=sigma * st[k], wrap_x=wrap_x)


def stamp_many(img, xs, ys, flux, rgb, sigma=1.0, sigma_x=None, r=None,
               wrap_x=True):
    """
    Add many Gaussian point sources at once.

    Same profile as frame.stamp, evaluated for every source in parallel and
    accumulated with bincount. rgb is either one colour for all sources or one
    row per source. wrap_x carries sources across the azimuth seam, which a
    panorama has and a framed view does not.

    sigma_x may be per-source and larger than sigma. The panorama stretches
    azimuth by 1/cos(alt), so a source drawn round here would come out as a
    vertical ellipse once the viewer undoes that stretch. Widening it in x by
    the same factor cancels out.
    """
    H, W = img.shape[:2]
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    flux = np.asarray(flux, dtype=float)
    if xs.size == 0:
        return
    sx = np.full(xs.shape, float(sigma)) if sigma_x is None else \
        np.broadcast_to(np.asarray(sigma_x, dtype=float), xs.shape).copy()
    if r is None:
        r = int(min(np.ceil(3.0 * max(sigma, float(sx.max()))), 64))

    ix = np.round(xs).astype(np.int64)
    iy = np.round(ys).astype(np.int64)
    off = np.arange(-r, r + 1)

    gx = (ix[:, None] + off[None, :]) - xs[:, None]           # (N, K)
    gy = (iy[:, None] + off[None, :]) - ys[:, None]
    wx = np.exp(-gx ** 2 / (2.0 * sx[:, None] ** 2))
    wy = np.exp(-gy ** 2 / (2.0 * sigma ** 2))
    wgt = (wy[:, :, None] * wx[:, None, :]
           / (2.0 * np.pi * sigma * sx[:, None, None]))

    X = ix[:, None, None] + off[None, None, :]
    Y = iy[:, None, None] + off[None, :, None]
    X = np.broadcast_to(X, wgt.shape)
    Y = np.broadcast_to(Y, wgt.shape)

    if wrap_x:
        X = X % W
        ok = (Y >= 0) & (Y < H)
    else:
        ok = (X >= 0) & (X < W) & (Y >= 0) & (Y < H)

    idx = (Y * W + X)[ok]
    base = wgt[ok]
    fl = np.broadcast_to(flux[:, None, None], wgt.shape)[ok]

    rgb = np.asarray(rgb, dtype=float)
    flat = img.reshape(-1, 3)
    n = flat.shape[0]
    for ch in range(3):
        if rgb.ndim == 1:
            w_ch = base * fl * rgb[ch]
        else:
            w_ch = base * fl * np.broadcast_to(
                rgb[:, ch][:, None, None], wgt.shape)[ok]
        flat[:, ch] += np.bincount(idx, weights=w_ch, minlength=n)


# ------------------------------------------------------------------ geometry

def grid(w, h, alt_max_deg):
    """Altitude and azimuth of every pixel. Azimuth increases to the right."""
    az = (np.arange(w) + 0.5) / w * 2.0 * np.pi
    alt = (1.0 - (np.arange(h) + 0.5) / h) * alt_max_deg * DEG
    return alt[:, None] + 0.0 * az[None, :], 0.0 * alt[:, None] + az[None, :]


def project(alt, az, w, h, alt_max_deg):
    x = az / (2.0 * np.pi) * w - 0.5
    y = (1.0 - alt / (alt_max_deg * DEG)) * h - 0.5
    return x, y


def pixel_arcsec2(h, w, alt_max_deg):
    """
    The solid angle a pixel would cover at the horizon, arcsec^2.

    Constant on purpose. This panorama is a map of surface brightness, so a
    patch of sky of a given brightness should come out the same shade wherever
    it sits, exactly as on a printed chart. The varying solid angle per pixel
    is handled where it actually matters, in the width of the point sources.
    """
    return float((360.0 / w) * 3600.0 * (alt_max_deg / h) * 3600.0)


def x_stretch(alt, cap=20.0):
    """
    1/cos(alt), the horizontal exaggeration of this projection.

    Capped because it diverges at the pole. At the cap the error is confined
    to the last three degrees around the zenith, which is a thousandth of the
    sky, and the alternative is a kernel wider than the panorama.
    """
    return np.minimum(1.0 / np.maximum(np.cos(alt), 1e-6), cap)


# ------------------------------------------------------------------- render

def render(cons, scale, lat, dec, ra_sun, ref_lst, mins_signed,
           w=2400, h=600, alt_max=90.0, bortle=1, model="boley",
           dt=0.0, background=None):
    """
    One panorama. Returns (linear RGB flux, sky brightness at the zenith,
    solar elevation, satellites visible).

    `background` lets an animation reuse the sky and stars, which do not move
    perceptibly over the couple of minutes an orbital time-lapse covers, and
    which cost as much to draw as the satellites do. Pass the array returned by
    render_background and only the satellites are redrawn.

    `dt` advances the constellation by this many seconds without touching the
    sky, which is what makes the satellites move and nothing else.
    """
    SK.SQM_ART = T.BORTLE[bortle]
    lst = ref_lst + mins_signed / 60.0
    s = L.sun_dir(dec)
    r_obs, up, east, north = L.observer(lat, lst)
    sun_el = float(np.degrees(np.arcsin(np.clip(s @ up, -1, 1))))
    sun_az = float(np.arctan2(s @ east, s @ north) % (2 * np.pi))

    if background is None:
        img, S_zen = render_background(lat, dec, ra_sun, ref_lst, mins_signed,
                                       w, h, alt_max, bortle)
    else:
        img, S_zen = background[0].copy(), background[1]

    n_vis = 0.0
    if cons is not None:
        f = L.observe if model == "boley" else L.observe_empirical
        for c in cons:
            pos = L.propagate(c, dt)
            a, z, d, V, lit = f(pos, r_obs, up, east, north, s)
            S_loc, _ = SK.brightness(a, z, sun_el, sun_az)
            k = (lit & np.isfinite(V) & (a > 0)
                 & (a < alt_max * DEG) & (V < T.limiting_mag(S_loc)))
            if not k.any():
                continue
            x, y = project(a[k], z[k], w, h, alt_max)
            stamp_points(img, x, y, 10.0 ** (-0.4 * V[k]) * scale,
                         np.array([0.95, 0.97, 1.0]), a[k], sigma=1.0)
            n_vis += k.sum() * scale
    return img, S_zen, sun_el, n_vis


def render_background(lat, dec, ra_sun, ref_lst, mins_signed,
                      w=2400, h=600, alt_max=90.0, bortle=1):
    """Sky and stars only. Everything here is fixed over an orbital time-lapse."""
    SK.SQM_ART = T.BORTLE[bortle]
    lst = ref_lst + mins_signed / 60.0
    s = L.sun_dir(dec)
    r_obs, up, east, north = L.observer(lat, lst)
    sun_el = float(np.degrees(np.arcsin(np.clip(s @ up, -1, 1))))
    sun_az = float(np.arctan2(s @ east, s @ north) % (2 * np.pi))

    alt, az = grid(w, h, alt_max)
    fsky, csky, S = SK.radiance(alt, az, sun_el, sun_az,
                                pixel_arcsec2(h, w, alt_max))
    img = fsky[..., None] * csky

    s_alt, s_az, s_mag, s_rgb = RS.sky(lst, ra_sun, lat)
    vis = (s_alt > 0) & (s_alt < alt_max * DEG)
    if vis.any():
        x, y = project(s_alt[vis], s_az[vis], w, h, alt_max)
        ext = L.K_EXT * L.airmass(s_alt[vis])
        stamp_points(img, x, y, 10.0 ** (-0.4 * (s_mag[vis] + ext)),
                     s_rgb[vis], s_alt[vis], sigma=1.15)

    S_zen = float(T.add_glow(T.sky_brightness(sun_el), T.BORTLE[bortle]))
    return img, S_zen


def visible_altaz(cons, lat, dec, ra_sun, ref_lst, mins_signed,
                  alt_max=90.0, bortle=1, model="boley"):
    """
    Where everything visible actually is, in radians.

    The viewer needs this to count what is inside a window the server never
    rendered. Same test as render(), so a satellite in this list is a satellite
    that got drawn.
    """
    SK.SQM_ART = T.BORTLE[bortle]
    lst = ref_lst + mins_signed / 60.0
    s = L.sun_dir(dec)
    r_obs, up, east, north = L.observer(lat, lst)
    sun_el = float(np.degrees(np.arcsin(np.clip(s @ up, -1, 1))))
    sun_az = float(np.arctan2(s @ east, s @ north) % (2 * np.pi))

    A, Z = [], []
    f = L.observe if model == "boley" else L.observe_empirical
    for c in cons:
        pos = L.propagate(c, 0.0)
        a, z, d, V, lit = f(pos, r_obs, up, east, north, s)
        S_loc, _ = SK.brightness(a, z, sun_el, sun_az)
        k = (lit & np.isfinite(V) & (a > 0) & (a < alt_max * DEG)
             & (V < T.limiting_mag(S_loc)))
        if k.any():
            A.append(a[k])
            Z.append(z[k])
    sat = (np.concatenate(A), np.concatenate(Z)) if A else \
        (np.zeros(0), np.zeros(0))

    s_alt, s_az, s_mag, _ = RS.sky(lst, ra_sun, lat)
    vis = (s_alt > 0) & (s_alt < alt_max * DEG)
    if vis.any():
        m = s_mag[vis] + L.K_EXT * L.airmass(s_alt[vis])
        Sl, _ = SK.brightness(s_alt[vis], s_az[vis], sun_el, sun_az)
        seen = m < T.limiting_mag(Sl)
        star = (s_alt[vis][seen], s_az[vis][seen])
    else:
        star = (np.zeros(0), np.zeros(0))
    return sat, star


def tonemap(img, S_zenith, h, w, alt_max):
    """
    frame.tonemap, with the panorama's own pixel scale.

    The reference pixel is taken at the horizon row, where the solid angle is
    largest, so the exposure does not swing with the chosen altitude range.
    """
    pix = pixel_arcsec2(h, w, alt_max)
    ref = 10.0 ** (-0.4 * (21.7 - 2.5 * np.log10(pix)))
    cur = 10.0 ** (-0.4 * (S_zenith - 2.5 * np.log10(pix)))
    x = img * (0.028 / ref * (ref / cur) ** 0.72)
    return (x / (1.0 + x)) ** (1 / 2.2)


def to_bytes(img, S_zenith, alt_max):
    h, w = img.shape[:2]
    out = tonemap(img, S_zenith, h, w, alt_max)
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)
