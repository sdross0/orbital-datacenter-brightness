"""
Orbital data centers: what the sky would look like from where you are.

Streamlit front end over the same modules that produce the video. No physics
lives here.

The picture is a whole-sky panorama handed to a WebGL viewer, not a fixed
frame. Panning and zooming happen in the browser, so they are immediate; the
server is only asked for a new sky when the physics changes.
"""
import datetime as dt

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

import lsm as L
import pano as P
import sky_view as SV
import solar
import viewer

st.set_page_config(page_title="Orbital data centers in the night sky",
                   layout="wide", initial_sidebar_state="expanded")

# Bump this whenever the physics changes. A stale copy of this app once showed
# satellites in August that the corrected model says are not there, and there
# was no way to tell from the screen which version had produced the picture.
VERSION = "2026-08-16"

# The panorama runs all the way to the zenith. Satellites do pass through it,
# and it is the darkest part of the sky, so it is where they show up best.
ALT_MAX = 90.0
# Powers of two, so the azimuth seam can wrap in the shader.
#
# Motion is not forced to be coarse by the renderer: a frame costs about the
# same at any size, because the time goes into stamping thirty thousand point
# sources, not into pixels. What sets the limit is the browser, which holds
# every frame decoded. A 4096 frame is 17 MB decoded, so sixty of them is a
# gigabyte. So the choice is frames against sharpness, and it is the same
# control as the still resolution: Standard buys smooth motion, High buys a
# sharp picture and half as many frames.
PANO = {
    "Standard": {"still": (4096, 1024), "motion": (2048, 512), "div": 1},
    "High": {"still": (8192, 2048), "motion": (4096, 1024), "div": 2},
}

SAT_COLOR = {"boley": "#ff9a3c", "mini": "#7ab8ff"}
STAR_COLOR = "#cfd8e8"
DIM = "#8b97a8"

# (frames, seconds of sky time per frame, speed menu, button text)
MOTION = {
    "Still": (1, 0.0, (), ""),
    "Satellites moving": (60, 1.0,
                          ((10, "10x"), (30, "30x"), (60, "60x")),
                          "Play orbital motion"),
    "The evening passing": (40, 360.0,
                            ((2, "720x"), (4, "1,440x"), (8, "2,880x")),
                            "Play the evening"),
}


# ----------------------------------------------------------------- physics


@st.cache_resource(show_spinner="Building the constellation...")
def base_constellation():
    return L.build_sso(500_000, relax_deg=10.0)


@st.cache_data(show_spinner=False)
def find_peak(lat, y, m, d, dusk, model, bortle):
    cons = base_constellation()
    return SV.peak_minutes(cons, 500_000 / L.total_of(cons),
                           y, m, d, lat, dusk, model, bortle)


@st.cache_data(show_spinner=False)
def count_now(lat, y, m, d, dusk, mins, bortle, model, n_sats):
    """
    Whole-sky count at this instant, cheaply. One satellite pass, no pixels.

    Used to decide whether an animation is worth rendering at all. Sixty
    frames of a sky with nothing in it costs half a minute and shows exactly
    what one frame would have shown.
    """
    base = base_constellation()
    cons, scale = SV.subsample(base, n_sats)
    return SV.whole_sky_count(cons, scale, y, m, d, lat, mins, dusk,
                              bortle, model)


@st.cache_data(show_spinner=False)
def ring_az(lat, y, m, d, mins, dusk, n_sats, model, bortle, hfov):
    base = base_constellation()
    cons, _ = SV.subsample(base, n_sats)
    return SV.ring_azimuth(cons, y, m, d, lat, mins, dusk, model, bortle, hfov)


@st.cache_data(show_spinner=False, max_entries=4)
def sky_state(lat, y, m, d, dusk, mins, bortle, model, n_sats, mode, res):
    """
    Everything the browser needs for one setting: the panorama or panoramas,
    the positions of what is visible, and the whole-sky counts.

    Frames come back already JPEG encoded. Sixty raw panoramas would be a
    couple of hundred megabytes to cache; sixty JPEGs are a few.

    In "satellites moving" the sky and stars are drawn once and reused across
    frames, since nothing but the constellation changes over a minute. In "the
    evening passing" the sky is the thing that changes, so it is redrawn.
    """
    n_frames, dt_step, _, _ = MOTION[mode]
    if n_frames > 1:
        # High resolution halves the frame count to stay inside the browser's
        # memory, and doubles the sky time each frame covers so the motion
        # still spans the same interval. It plays a little steppier.
        n_frames = max(n_frames // PANO[res]["div"], 2)
        dt_step *= PANO[res]["div"]
    dec, ra = solar.sun(y, m, d)
    ss = solar.sunset_lst(lat, dec)
    ref = ss if dusk else solar.sunrise_lst(lat, dec)
    sgn = 1.0 if dusk else -1.0
    signed = sgn * mins

    base = base_constellation()
    cons, scale = SV.subsample(base, n_sats)
    w, h = PANO[res]["still" if n_frames == 1 else "motion"]
    evening = mode.startswith("The evening")

    bg = None if evening else P.render_background(
        lat, dec, ra, ref, signed, w, h, ALT_MAX, bortle)

    frames, n_view, sun_el = [], 0.0, 0.0
    prog = st.progress(0.0, text="Rendering...") if n_frames > 1 else None
    for i in range(n_frames):
        if evening:
            m_i = sgn * (i * dt_step / 60.0)
            img, S_zen, sun_el, n = P.render(cons, scale, lat, dec, ra, ref,
                                             m_i, w, h, ALT_MAX, bortle,
                                             model, 0.0, None)
        else:
            img, S_zen, sun_el, n = P.render(cons, scale, lat, dec, ra, ref,
                                             signed, w, h, ALT_MAX, bortle,
                                             model, i * dt_step, bg)
        frames.append(viewer.encode(P.to_bytes(img, S_zen, ALT_MAX),
                                    82 if n_frames == 1 else 74))
        n_view = max(n_view, n)
        if prog is not None:
            prog.progress((i + 1) / n_frames,
                          text="Rendering frame %d of %d..." % (i + 1, n_frames))
    if prog is not None:
        prog.empty()

    sat, star = P.visible_altaz(cons, lat, dec, ra, ref, signed,
                                ALT_MAX, bortle, model)
    n_all = SV.whole_sky_count(cons, scale, y, m, d, lat, mins, dusk,
                               bortle, model)
    el_now, s_all = SV.star_counts_zenith(lat, dec, ra, ref, signed, bortle)
    return (frames, viewer.pairs(*sat), viewer.pairs(*star), scale,
            float(el_now), int(round(n_all)), int(s_all), ref, w)


# ----------------------------------------------------------------- controls

st.title("What would orbital data centers look like from your sky?")
st.caption("The sun-synchronous half of SpaceX's FCC filing, propagated and "
           "rendered with two published brightness models. Pick a place, a "
           "date and a time, then drag the sky around.")

sb = st.sidebar
sb.header("Where and when")
lat = sb.number_input("Your latitude (degrees north, negative for south)",
                      -75.0, 75.0, 37.2, 0.1,
                      help="Longitude does not matter here. This constellation "
                           "depends on latitude and local solar time.")
lat = round(float(lat), 1)          # one value everywhere, so the caches agree
date = sb.date_input("Date", dt.date.today())
when = sb.radio("Twilight", ["Evening (after sunset)", "Morning (before sunrise)"])
dusk = when.startswith("Evening")

sb.header("Sky and model")
model_label = sb.radio("Brightness model", ["No mitigation", "Optimistic mitigation"])
model = "boley" if model_label == "No mitigation" else "mini"
n_sats = sb.select_slider(
    "Satellites in orbit",
    options=[1000, 5000, 10000, 25000, 50000, 100000, 200000, 300000, 400000, 500000],
    value=500000, format_func=lambda v: f"{v:,}")
bortle = sb.select_slider("Light pollution (Bortle class)",
                          options=[1, 2, 3, 4, 5, 6, 7, 8], value=1,
                          help="1 is a pristine dark site, 8 is an inner city. "
                               "There is no automatic lookup, so set it by hand.")

peak_m, peak_n = find_peak(lat, date.year, date.month, date.day,
                           dusk, model, bortle)
label = "after sunset" if dusk else "before sunrise"

# The clock is deliberately not tied to the peak. The two models peak ten
# minutes apart, so defaulting to each model's own peak silently moved the
# clock when you switched between them, which is exactly the comparison
# someone wants to make. It stays where you put it; the button below jumps.
st.session_state.setdefault("mins", 80)


def _goto_peak():
    # Has to be a callback. Assigning to a widget's key from the body of the
    # script after that widget exists is an error in Streamlit; from inside a
    # callback it is the supported way, because the callback runs before the
    # rerun that rebuilds the widget.
    st.session_state.mins = int(st.session_state.peak_target)


mins = sb.slider("Minutes %s" % label, 0, 240, key="mins", step=2)
if peak_m is not None and peak_n > 0:
    if int(peak_m) == int(st.session_state.mins):
        sb.caption("This is the peak for this model, date and latitude.")
    else:
        sb.caption("Peak for this model is **%d minutes %s**." % (peak_m, label))
        st.session_state.peak_target = int(peak_m)
        sb.button("Go to %d minutes" % peak_m, use_container_width=True,
                  on_click=_goto_peak)

sb.header("Motion")
mode = sb.radio("What moves", list(MOTION.keys()),
                help="Satellites moving holds the clock still and advances the "
                     "orbits a second at a time. The evening passing holds the "
                     "orbits and runs the clock from sunset to the small hours.")

# Do not render an animation of an empty sky. Both checks are one satellite
# pass, against roughly thirty seconds for the frames they save.
no_motion = None
if mode == "Satellites moving":
    if count_now(lat, date.year, date.month, date.day, dusk, mins,
                 bortle, model, n_sats) < 1:
        no_motion = ("Nothing is visible at this minute under this model, so "
                     "there is nothing to set moving. Move the clock, or "
                     "switch to the no-mitigation model.")
elif mode == "The evening passing":
    if not peak_n or peak_n < 1:
        no_motion = ("Nothing is visible at any point this evening under this "
                     "model. At this latitude the optimistic case disappears "
                     "entirely between about 13 April and 30 August, when "
                     "these satellites spend the night in Earth's shadow. Try "
                     "a date in autumn or winter.")

if no_motion:
    mode = "Still"
    sb.info(no_motion)
elif mode != "Still":
    sb.caption("Rendering this takes a few seconds the first time. After that "
               "it is cached, and the speed menu costs nothing.")

sb.header("Where you are looking")


def _aim():
    st.session_state.az = int(st.session_state.ring_target)


# Aiming at the ring used to be a checkbox, and that was a mistake: the densest
# azimuth moves through the evening, so leaving it ticked quietly swung the
# view every time the clock moved, which is the one thing you do not want while
# comparing two times. It is an action now, not a mode.
st.session_state.setdefault("az", 315)
az0 = sb.slider("Compass heading (degrees)", 0, 359, key="az", step=5)
el0 = sb.slider("Elevation, degrees above the horizon", 0, 89, 25, 1)
fov0 = sb.slider("Field of view (degrees wide)", 30, 120, 90, 2)
res = sb.radio("Resolution", list(PANO.keys()), horizontal=True,
               help="Standard is about 11 pixels per degree and gives sixty "
                    "motion frames. High is 23 per degree, takes a few seconds "
                    "longer, and halves the motion frames to stay inside the "
                    "browser's memory. Not every graphics card will take a "
                    "texture 8192 pixels wide; the viewer says so if yours "
                    "will not.")
tall = sb.checkbox("Large view", value=False,
                   help="Makes the sky panel taller. There is also a "
                        "fullscreen button under the sky itself.")
canvas_h = 860 if tall else 520

# ----------------------------------------------------------------- render

if solar.sunset_lst(lat, solar.sun(date.year, date.month, date.day)[0]) is None:
    st.warning("At this latitude and date the Sun does not rise or set, so "
               "there is no twilight. Try another date or a lower latitude.")
    st.stop()

(frames, sat_pairs, star_pairs, scale, sun_el, n_all, s_all, ref,
 tex_w) = sky_state(lat, date.year, date.month, date.day, dusk, mins,
                    bortle, model, n_sats, mode, res)

ring = ring_az(lat, date.year, date.month, date.day, mins, dusk,
               n_sats, model, bortle, fov0)
if ring is not None:
    off = abs(((ring - az0 + 180) % 360) - 180)
    st.session_state.ring_target = int(round(ring)) // 5 * 5
    sb.button("Aim at the densest sky (%d deg %s)"
              % (round(ring), SV.point_name(ring)),
              use_container_width=True, on_click=_aim, disabled=off < 3)
    sb.caption("The fullest %d degree window at this minute, for this model. "
               "It moves through the evening, so this aims once rather than "
               "following it." % fov0)

n_frames, dt_step, speeds, play_label = MOTION[mode]

c1, c2 = st.columns([3, 1])

with c1:
    components.html(
        viewer.html(frames, ALT_MAX, sat_pairs, scale, star_pairs, 1.0,
                    yaw=az0, pitch=el0, fov=fov0, canvas_h=canvas_h,
                    sat_color=SAT_COLOR[model],
                    speeds=speeds or ((1, "1x"),),
                    play_label=play_label or "Play", tex_w=tex_w,
                    view_key="%d_%d_%d" % (az0, el0, fov0)),
        height=canvas_h + 90, scrolling=False)

with c2:
    sat = SAT_COLOR[model]
    st.markdown(
        """
<div style="display:grid;grid-template-columns:auto 1fr;
            gap:2px 14px;align-items:baseline;margin-bottom:10px">
  <div></div>
  <div style="font-size:.68rem;letter-spacing:.09em;text-transform:uppercase;
              color:{dim};text-align:right">whole sky</div>

  <div style="font-size:.88rem;color:{sat}">satellites</div>
  <div style="font-size:2.0rem;font-weight:600;color:{sat};
              text-align:right;line-height:1.1">{na}</div>

  <div style="font-size:.88rem;color:{star}">stars</div>
  <div style="font-size:2.0rem;font-weight:600;color:{star};
              text-align:right;line-height:1.1">{sa}</div>
</div>
""".format(dim=DIM, sat=sat, star=STAR_COLOR,
           na=f"{n_all:,}", sa=f"{s_all:,}"),
        unsafe_allow_html=True)
    st.caption("Counts for the view you are looking at are in the bar under "
               "the sky, and follow you as you drag.")

    if s_all > 0 and n_all > 0:
        if n_all >= s_all:
            st.markdown("Across the whole sky, satellites outnumber stars "
                        "**%.0f to 1**." % (n_all / s_all))
        else:
            st.markdown("Across the whole sky, stars still outnumber "
                        "satellites **%.0f to 1**." % (s_all / n_all))

    st.divider()
    st.write("**Sun** %.1f degrees below the horizon" % abs(sun_el))
    hh, mm = int(ref), int(round((ref % 1) * 60))
    if mm == 60:
        hh, mm = hh + 1, 0
    st.write("**%s** %d:%02d %s, sun time"
             % ("Sunset" if dusk else "Sunrise",
                12 if hh % 12 == 0 else hh % 12, mm,
                "am" if hh < 12 else "pm"))
    st.caption("Sun time, not clock time: it is noon when the Sun is highest. "
               "Your clock can differ by an hour or more depending on where "
               "you sit in your time zone, and another hour in summer.")

    if n_all < 1:
        st.info("Nothing visible anywhere. Either the sky is still too bright "
                "or the satellites are all in Earth's shadow.")

with st.expander("What this is, and what it is not"):
    st.markdown("""
**Dragging is a browser trick, and an honest one.** The server renders the
whole dome once, as a map in altitude and azimuth. The viewer then cuts a
correct perspective window out of that map on the graphics card, which is the
same projection the video frames use, so the geometry you drag around is the
geometry that was computed. What it is not is a new physics calculation per
frame: move the time slider or change the model and the server renders again.

**The counts in the bar follow the view.** They come from the positions of
everything that beat the sky where it sits, thinned to a sample and scaled
back up, so they carry a little sampling noise at small numbers. The whole-sky
figures beside the picture are exact and are the ones to quote.

**Field of view.** Two eyes together take in roughly 200 degrees from side to
side, about 114 of it in stereo, but nearly all of that is peripheral: sharp
vision covers some 2 degrees and useful detail about 30. None of those can be
the answer here, because a flat rectilinear image cannot hold 200 degrees and
it stretches whatever sits off-axis. Natural perspective would be near 60, a
50 mm lens. The default is 90, because the ring is a structure a hundred
degrees across and at 60 the horizon leaves the frame.

**Orbits** are the sun-synchronous groups in Table 1 of SpaceX's 29 May 2026
FCC supplement: up to 500,000 satellites between 565 and 1,002 km, dawn-dusk,
with a 10 degree spread in ascending node. The roughly half of the filing near
30 degrees inclination is not included.

**No mitigation** is the Lambertian sphere reference from Boley, Lawler & Rein
2026, arXiv:2608.02757. It is what these do if nobody tries.

**Optimistic mitigation** uses the measured on-orbit brightness of a Starlink
Gen2 Mini in its darkening mode (Mallama et al. 2023, arXiv:2306.06657),
scaled up for AI1's larger area. It assumes mitigation transfers to a
spacecraft roughly six times bigger, which is an assumption, not a measurement.

**Season matters more than you would guess**, especially for the optimistic
model. Near a solstice the geometry front-lights the satellites at small phase
angles, where the measured phase function is several magnitudes brighter than
at the side-lit angles you get near an equinox.

**Sky brightness** is calibrated to measurement at the zenith and modelled in
shape across the rest of the sky. Artificial skyglow is added from the Bortle
setting and carried across the dome with the same geometry as airglow, which
is approximate: a real light dome points at whatever town is nearest. A
satellite or star is drawn only if it beats the sky at its own position, so
the counts and the picture agree.

**Stars** are real: 8,913 brighter than magnitude 6.5, in correct positions
for the date.

Neither model is a prediction. The gap between them is the point, and it would
close if SpaceX published an expected magnitude and phase function for AI1.

Code and assumptions:
https://github.com/sdross0/orbital-datacenter-brightness
""")
