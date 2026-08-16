"""
Render one sky, for any latitude, date, time and heading.

Wraps the same modules the video uses. Nothing here re-implements physics; it
only sets the observer and hands off to frame.render.
"""
import numpy as np
import lsm as L
import frame as F
import twilight as T
import skymodel as SK
import realstars as RS
import solar
from PIL import Image, ImageDraw, ImageFont

# 16-point compass. Index by round(az / 22.5) % 16.
POINTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def point_name(az_deg):
    return POINTS[int(round((az_deg % 360) / 22.5)) % 16]

# Font lookup has to work on macOS, Linux and whatever the host container has.
_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Regular.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _font(size):
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size)      # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def subsample(cons, n_want, n_full=500_000):
    """Thin the constellation to n_want satellites by slicing each plane."""
    if n_want >= n_full:
        return cons, n_full / L.total_of(cons)
    out = []
    frac = max(n_want / n_full, 1e-6)
    for c in cons:
        per = max(int(round(c["th0"].shape[1] * frac)), 1)
        d = dict(c)
        d["th0"] = c["th0"][:, :per]
        d["total"] = c["th0"].shape[0] * per
        out.append(d)
    tot = sum(c["total"] for c in out)
    return out, n_want / max(tot, 1)


def _text_w(d, s, f):
    try:
        return d.textlength(s, font=f)
    except AttributeError:
        return d.textsize(s, font=f)[0]


def compass(img, az0, hfov):
    """
    Compass headings along the bottom, as on a star chart.

    Ticks sit above their labels rather than through them. The eight principal
    points are labelled; the sixteenths get a shorter tick and no text, which
    gives a sense of scale without adding words to read.
    """
    im = Image.fromarray(img)
    W, H = im.size
    d = ImageDraw.Draw(im, "RGBA")
    size = max(13, int(W / 50))
    f = _font(size)
    foc = (W / 2) / np.tan(np.radians(hfov / 2))

    y_lab = H - 8 - size                 # top of the text
    y_tick = y_lab - 5                   # ticks stop here, clear of the text

    # All sixteen points are labelled. At a 60 degree field only two or three
    # are in frame, so labelling only the eight principal ones would often
    # leave none at all. The principal points get a longer, brighter tick.
    for i in range(16):
        a = i * 22.5
        da = (a - az0 + 180) % 360 - 180
        if abs(da) > hfov / 2 + 1:
            continue
        x = W / 2 + foc * np.tan(np.radians(da))
        if not (4 < x < W - 4):
            continue
        major = (i % 2 == 0)
        d.line([x, y_tick - (14 if major else 8), x, y_tick],
               fill=(214, 226, 244, 225) if major else (190, 202, 222, 160),
               width=2 if major else 1)
        nm = POINTS[i]
        tw = _text_w(d, nm, f)
        if tw / 2 < x < W - tw / 2:
            # An outline rather than a panel behind it. A dark box here would
            # cover satellites, which is the thing we are trying to show.
            d.text((x - tw / 2, y_lab), nm, font=f,
                   fill=(222, 232, 248, 245) if major else (198, 210, 230, 205),
                   stroke_width=2, stroke_fill=(6, 8, 14, 205))
    return np.asarray(im)


def peak_minutes(cons, scale, year, month, day, lat, dusk=True,
                 model="boley", bortle=1, lo=0, hi=240, step=10):
    """When the count is largest. Counts only, no rendering, so it is quick."""
    dec, _ = solar.sun(year, month, day)
    ss = solar.sunset_lst(lat, dec)
    if ss is None:
        return None, 0.0
    ref = ss if dusk else solar.sunrise_lst(lat, dec)
    s = L.sun_dir(dec)
    f = L.observe if model == "boley" else L.observe_empirical
    best = (None, -1.0)
    for m in range(lo, hi + 1, step):
        lst = ref + (m if dusk else -m) / 60.0
        el = L.sun_elevation(lat, lst, dec)
        if el > 0:
            continue
        vl = float(T.nelm(el, BORTLE_SQM[bortle]))
        r, u, e, n = L.observer(lat, lst)
        tot = 0.0
        for c in cons:
            p = L.propagate(c, 0.0)
            a, z, dd, V, lit = f(p, r, u, e, n, s)
            tot += (lit & np.isfinite(V) & (a > -0.005) & (V < vl)).sum() * scale
        if tot > best[1]:
            best = (m, tot)
    return best


def whole_sky_count(cons, scale, year, month, day, lat, mins, dusk=True,
                    bortle=1, model="boley"):
    dec, _ = solar.sun(year, month, day)
    ss = solar.sunset_lst(lat, dec)
    if ss is None:
        return 0.0
    ref = ss if dusk else solar.sunrise_lst(lat, dec)
    lst = ref + (mins if dusk else -mins) / 60.0
    el = L.sun_elevation(lat, lst, dec)
    if el > 0:
        return 0.0
    vl = float(T.limiting_mag(T.add_glow(T.sky_brightness(el), BORTLE_SQM[bortle])))
    r, u, e, n = L.observer(lat, lst)
    s = L.sun_dir(dec)
    f = L.observe if model == "boley" else L.observe_empirical
    tot = 0.0
    for c in cons:
        p = L.propagate(c, 0.0)
        a, z, dd, V, lit = f(p, r, u, e, n, s)
        tot += (lit & np.isfinite(V) & (a > -0.005) & (V < vl)).sum() * scale
    return tot

BORTLE_SQM = T.BORTLE


def configure(lat, dec, ra_sun, sunset_lst, az, el, hfov, w, h, bortle):
    F.W, F.H, F.HFOV, F.AZ0, F.EL0 = w, h, hfov, az, el
    F.LAT, F.DEC, F.RA_SUN, F.SUNSET_LST = lat, dec, ra_sun, sunset_lst
    # This is the switch that makes light pollution real. Every limit in
    # frame.render comes back through skymodel.brightness, so setting it here
    # dims the picture and the count together.
    SK.SQM_ART = BORTLE_SQM[bortle]
    F.FOC = (w / 2) / np.tan(np.radians(hfov / 2))
    F.CX, F.CY = w / 2.0, h / 2.0
    F.PIX_ARCSEC2 = (hfov * 3600.0 / w) ** 2
    F.FWD, F.RIGHT, F.UP = F.basis(az, el)


def render(cons, scale, year, month, day, lat, mins, dusk=True,
           az=315.0, el=27.0, hfov=86.0, w=960, h=540, bortle=1,
           model="boley"):
    """mins is minutes after sunset, or before sunrise if dusk is False."""
    dec, ra = solar.sun(year, month, day)
    ss = solar.sunset_lst(lat, dec)
    if ss is None:
        return None, None, None, None
    ref = ss if dusk else solar.sunrise_lst(lat, dec)
    signed = mins if dusk else -mins
    configure(lat, dec, ra, ref, az, el, hfov, w, h, bortle)
    img, sun_el, S, n = F.render(signed, model, cons, scale, 1.0)
    out = F.tonemap(img, float(S[h // 2, w // 2]))
    return (np.clip(out, 0, 1) * 255).astype(np.uint8), sun_el, n, dec


def star_counts(lat, dec, ra_sun, ref_lst, mins_signed, bortle=1):
    """
    Stars visible to the unaided eye, in this view and over the whole sky.

    Call straight after render(), which leaves the camera configured. In-view
    stars are tested against the sky at their own position, the same test the
    renderer applies to satellites, so the number agrees with the picture.
    The whole-sky figure uses the zenith limit, which is the convention the
    repository and the papers quote.
    """
    lst = ref_lst + mins_signed / 60.0
    sun_el, sun_az = F.sun_altaz(mins_signed)
    s_alt, s_az, mag, _ = RS.sky(lst, ra_sun, lat)
    vis = s_alt > 0
    if not vis.any():
        return 0, 0
    alt, az, mag = s_alt[vis], s_az[vis], mag[vis]
    m_obs = mag + L.K_EXT * L.airmass(alt)

    S_loc, _ = SK.brightness(alt, az, sun_el, sun_az)
    seen = m_obs < T.limiting_mag(S_loc)

    zen = T.limiting_mag(T.add_glow(T.sky_brightness(sun_el), BORTLE_SQM[bortle]))
    n_all = int((m_obs < zen).sum())

    x, y, front = F.project(alt, az)
    inframe = front & (x >= 0) & (x < F.W) & (y >= 0) & (y < F.H)
    return int((seen & inframe).sum()), n_all


def star_counts_zenith(lat, dec, ra_sun, ref_lst, mins_signed, bortle=1):
    """
    Whole-sky star count against the zenith limit, and the solar elevation.

    No camera required, unlike star_counts, so it is safe to call when nothing
    has configured frame.py.
    """
    lst = ref_lst + mins_signed / 60.0
    s = L.sun_dir(dec)
    r, u, e, n = L.observer(lat, lst)
    sun_el = float(np.degrees(np.arcsin(np.clip(s @ u, -1, 1))))
    s_alt, s_az, mag, _ = RS.sky(lst, ra_sun, lat)
    vis = s_alt > 0
    if not vis.any():
        return sun_el, 0
    m_obs = mag[vis] + L.K_EXT * L.airmass(s_alt[vis])
    zen = T.limiting_mag(T.add_glow(T.sky_brightness(sun_el),
                                    BORTLE_SQM[bortle]))
    return sun_el, int((m_obs < zen).sum())


def pixel_to_altaz(x, y, az0, el0, hfov, w, h):
    """
    Where a given pixel points, in degrees.

    Deliberately free of module state: the caller passes the camera, so this
    stays correct even when the frame it refers to came out of a cache and
    frame.py was last configured for something else.
    """
    foc = (w / 2.0) / np.tan(np.radians(hfov / 2.0))
    fwd, right, up = F.basis(az0, el0)
    d = foc * fwd + (x - w / 2.0) * right + (h / 2.0 - y) * up
    d = d / np.linalg.norm(d)
    return (float(np.degrees(np.arcsin(np.clip(d[2], -1.0, 1.0)))),
            float(np.degrees(np.arctan2(d[0], d[1])) % 360.0))


def corner_stretch(hfov, w, h):
    """
    Area magnification at the corner of a gnomonic frame.

    A flat image of a curved sky cannot be faithful everywhere. This is the
    factor by which a patch of sky in the corner is drawn larger than the same
    patch at the center, which is Tufte's lie factor for this projection: 1.0
    is honest, and it grows without bound as the field approaches 180 degrees.
    """
    foc = (w / 2) / np.tan(np.radians(hfov / 2))
    theta = np.arctan(np.hypot(w / 2, h / 2) / foc)
    return float(1.0 / np.cos(theta) ** 3)


def ring_azimuth(cons, year, month, day, lat, mins, dusk=True,
                 model="boley", bortle=1, hfov=90.0):
    """
    The heading that puts the most satellites in frame.

    Not the mean azimuth, which is what this used to return and which is the
    wrong statistic. The ring is often two lobes with a gap between them, and
    the circular mean of two lobes lands in the gap: at the December solstice
    the unmitigated distribution peaks near 175 and 335 degrees, and its mean
    is 253, a direction that is comparatively empty. This instead slides a
    window the width of the field of view around the horizon and returns the
    centre of the fullest one, which is the question the user is asking.

    The model matters too, and the earlier version ignored it. The two
    brightness models put their satellites in quite different parts of the
    sky, because the mitigated ones only clear the limit where the geometry
    favours them.
    """
    dec, _ = solar.sun(year, month, day)
    ss = solar.sunset_lst(lat, dec)
    if ss is None:
        return None
    ref = ss if dusk else solar.sunrise_lst(lat, dec)
    lst = ref + (mins if dusk else -mins) / 60.0
    r, u, e, n = L.observer(lat, lst)
    s = L.sun_dir(dec)
    sun_el = float(np.degrees(np.arcsin(np.clip(s @ u, -1, 1))))
    vlim = float(T.nelm(sun_el, BORTLE_SQM[bortle]))
    f = L.observe if model == "boley" else L.observe_empirical

    nb = 180                                   # 2 degree bins
    hist = np.zeros(nb)
    for c in cons:
        p = L.propagate(c, 0.0)
        alt, az, d, V, lit = f(p, r, u, e, n, s)
        k = lit & np.isfinite(V) & (alt > 0) & (V < vlim)
        if k.any():
            hist += np.histogram(np.degrees(az[k]) % 360.0,
                                 bins=nb, range=(0.0, 360.0))[0]
    if hist.sum() < 1:
        return None

    w = max(int(round(hfov / (360.0 / nb))), 1)
    tiled = np.concatenate([hist, hist, hist])
    smooth = np.convolve(tiled, np.ones(w), "same")[nb:2 * nb]
    return float((smooth.argmax() + 0.5) * (360.0 / nb))
