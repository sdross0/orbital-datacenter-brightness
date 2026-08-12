"""
The evening, plotted: how many satellites are visible to the unaided eye as a
function of time after sunset, under both brightness models, against the stars.

A table cannot show this well. The mitigated case is visible for only about
44 minutes, and the two models peak at different times, so anything coarser
than a few minutes hides the shape.

The naked-eye limit is recomputed at every step from the solar elevation
(twilight.py), so the curves fold together three things: the sky darkening,
the satellites entering eclipse, and the geometry of the ring.

Writes assets/evening.png. Requires numpy and matplotlib.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import lsm as L
import twilight as T
import stars as ST

N_SATS, LAT, DEC = 500_000, 37.23, 0.0
MINS = np.arange(0.0, 201.0, 2.0)
OUT = "assets/evening.png"

BG, ORA, BLU = "#0b1020", "#ffd0b0", "#a8d4ff"
STG, GRID, TXT = "#c8cfdd", "#232c44", "#dfe6f2"
FDIR = "/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-%s.otf"


def font(bold=False):
    try:
        return fm.FontProperties(fname=FDIR % ("Bold" if bold else "Regular"))
    except Exception:
        return None


def sweep():
    cons = L.build_sso(N_SATS, relax_deg=10.0)
    scale = N_SATS / L.total_of(cons)
    alt_s, az_s, mag_s = ST.sample_sky(m_limit=7.5)
    V_star = mag_s + L.K_EXT * L.airmass(alt_s)
    s = L.sun_dir(DEC)
    un, mi, st, vl = [], [], [], []
    for m in MINS:
        lst = 18.0 + m / 60.0
        el = L.sun_elevation(LAT, lst, DEC)
        lim = float(T.nelm(el))
        r_obs, up, east, north = L.observer(LAT, lst)
        a = b = 0.0
        for c in cons:
            pos = L.propagate(c, 0.0)
            for model, f in (("u", L.observe), ("m", L.observe_empirical)):
                alt, az, d, V, lit = f(pos, r_obs, up, east, north, s)
                ok = lit & np.isfinite(V) & (alt > -0.005) & (V < lim)
                if model == "u":
                    a += ok.sum() * scale
                else:
                    b += ok.sum() * scale
        un.append(a); mi.append(b); vl.append(lim)
        st.append(int((V_star < lim).sum()))
    return map(np.array, (un, mi, st, vl))


def main():
    un, mi, st, vl = sweep()
    fp, fb = font(), font(True)
    nz = MINS[mi > 0.5]
    lo, hi, pk = nz.min(), nz.max(), MINS[mi.argmax()]

    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(10, 8.2), dpi=170, sharex=True,
                                   gridspec_kw=dict(height_ratios=[1, 2.5], hspace=0.10))
    fig.patch.set_facecolor(BG)
    for a in (ax0, ax1):
        a.set_facecolor(BG); a.grid(True, color=GRID, lw=0.7); a.set_axisbelow(True)
        for sp in a.spines.values():
            sp.set_color(GRID)
        a.tick_params(colors=TXT, labelsize=10)
        for t in a.get_xticklabels() + a.get_yticklabels():
            if fp:
                t.set_fontproperties(fp)
        a.axvspan(0, 30, color="#ffffff", alpha=0.045, lw=0)
        for mm in (30, 60, 90):
            a.axvline(mm, color=GRID, lw=0.9, ls=":")

    ax0.plot(MINS, vl, color=TXT, lw=2.2)
    ax0.set_ylim(-2, 7.4); ax0.set_xlim(0, 200)
    ax0.set_ylabel("naked-eye limit\n(V)", color=TXT, fontsize=11, fontproperties=fp)
    ax0.axhline(6.48, color=GRID, lw=1.0, ls="--")
    ax0.text(197, 6.62, "dark-sky limit 6.5", ha="right", color="#8b98b5",
             fontsize=9.5, fontproperties=fp)
    ax0.text(14, 2.2, "sky too bright\nto see anything", ha="center",
             color="#8b98b5", fontsize=9.5, fontproperties=fp)
    for mm, lab in ((30, "civil"), (60, "nautical"), (90, "astronomical")):
        ax0.text(mm + 2.5, -1.5, lab + "\ntwilight ends", color="#7f8ca8",
                 fontsize=8.5, fontproperties=fp, va="bottom")

    ax1.axvspan(lo, hi, color=BLU, alpha=0.07, lw=0)
    ax1.plot(MINS, np.maximum(un, 0.6), color=ORA, lw=2.8)
    ax1.plot(MINS, np.maximum(mi, 0.6), color=BLU, lw=2.8)
    ax1.plot(MINS, np.maximum(st, 0.6), color=STG, lw=1.6, ls="--")
    ax1.set_yscale("log"); ax1.set_ylim(1, 9e4); ax1.set_xlim(0, 200)
    ax1.set_yticks([1, 10, 100, 1000, 10000])
    ax1.set_yticklabels(["1", "10", "100", "1,000", "10,000"])
    ax1.set_xlabel("minutes after sunset", color=TXT, fontsize=12,
                   fontproperties=fp, labelpad=8)
    ax1.set_ylabel("number visible to the unaided eye", color=TXT, fontsize=12,
                   fontproperties=fp, labelpad=8)
    ax1.annotate("unmitigated reference\npeak %s at %.0f min" % (f"{un.max():,.0f}", MINS[un.argmax()]),
                 xy=(MINS[un.argmax()], un.max()), xytext=(92, 47000), color=ORA,
                 fontsize=11.5, fontproperties=fp,
                 arrowprops=dict(arrowstyle="-", color=ORA, lw=1.0, alpha=.5))
    ax1.annotate("optimistic mitigated reference\nvisible only %.0f to %.0f min, peak %s"
                 % (lo, hi, f"{mi.max():,.0f}"),
                 xy=(pk, mi.max()), xytext=(108, 60), color=BLU,
                 fontsize=11.5, fontproperties=fp,
                 arrowprops=dict(arrowstyle="-", color=BLU, lw=1.0, alpha=.5))
    ax1.annotate("stars (%s once dark)" % f"{st[-1]:,}", xy=(140, st[-1]),
                 xytext=(120, 700), color=STG, fontsize=11, fontproperties=fp,
                 arrowprops=dict(arrowstyle="-", color=STG, lw=1.0, alpha=.5))
    ax1.text(158, 26000, "unmitigated exceeds the stars\nfor about two and a half hours",
             ha="center", color=ORA, fontsize=10, fontproperties=fp, alpha=.85)
    ax1.text(pk, 2.6, "mitigated never\nreaches the stars", ha="center",
             color=BLU, fontsize=10, fontproperties=fp, alpha=.85)

    ax0.set_title("What the evening actually looks like", color="#ffffff",
                  fontsize=17, fontproperties=fb, loc="left", pad=30)
    ax0.text(0, 1.045, "500,000 satellites, Blacksburg VA, equinox, naturally dark sky",
             transform=ax0.transAxes, color="#93a2bf", fontsize=10.5, fontproperties=fp)
    fig.savefig(OUT, facecolor=BG, bbox_inches="tight")
    print("wrote %s" % OUT)
    print("unmitigated: %s to %s min, peak %s at %.0f min"
          % (f"{MINS[un > 0.5].min():.0f}", f"{MINS[un > 0.5].max():.0f}",
             f"{un.max():,.0f}", MINS[un.argmax()]))
    print("mitigated  : %.0f to %.0f min, peak %s at %.0f min"
          % (lo, hi, f"{mi.max():,.0f}", pk))


if __name__ == "__main__":
    main()
