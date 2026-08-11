"""
Lambertian sphere photometry and the SXODC orbit distribution, following
Boley, Lawler & Rein (2026), "Rings in the Sky", arXiv:2608.02757.

Their model, their parameters. The point of this module is to reproduce the
published reference rather than to invent a better one:

    V = -26.77 - 2.5 log10[ (2 zeta / 3 pi^2) ((pi - phi) cos phi + sin phi) ]
        + 5 log10 R + k chi(Z)                                        (their eq 2)

    zeta = albedo x cross-section = 0.2 x 800 m^2 = 160 m^2
    k    = 0.15 mag / airmass, Kasten & Young (1989) airmass
    R    = slant range, metres (same length unit as zeta)

Provenance of each number:
    800 m^2 area   SpaceX supplement to the FCC, 29 May 2026 (via the paper)
    0.2 albedo     the authors' assumption, not a filed value
    500/1000/2000  Schedule S, SAT-LOA-20260108-00016, planes 1-3
    97.4/99.5/104.9 Schedule S inclinations; equal to sun-synchronous to 0.02 deg
    +/-30 deg RAAN Schedule S nodal tolerance (the paper's "relaxed" case uses 10)
    1,000,000      SpaceX filing headline

Not included: the ~30 deg inclination shell that appears in the May supplement.
That component dominates low and mid-latitude sky cover in the paper, so counts
produced here are a floor, not an estimate.
"""

import numpy as np

DEG = np.pi / 180.0
R_E = 6378.137                      # km, equatorial, as the paper uses
MU = 398600.4418
J2 = 1.08263e-3
OBLIQ = 23.4392811

ZETA = 0.2 * 800.0                  # m^2, albedo x cross-section
K_EXT = 0.15                        # mag per airmass
V_SUN = -26.77                      # the paper's solar constant term

# Schedule S planes 1-3: altitude km, inclination deg
SHELLS = ((500.0, 97.4), (1000.0, 99.5), (2000.0, 104.9))


# --------------------------------------------------------------- geometry
def sso_inclination(alt_km):
    """Inclination whose J2 nodal precession equals one revolution per year."""
    a = R_E + alt_km
    n = np.sqrt(MU / a ** 3)
    w_p = 2 * np.pi / (365.2422 * 86400.0)
    return np.degrees(np.arccos(-2 * w_p * a ** 2 / (3 * J2 * n * R_E ** 2)))


def sun_dir(dec_deg=0.0):
    """Unit vector to the Sun. Sub-solar longitude is fixed at 0 by choice."""
    d = dec_deg * DEG
    return np.array([np.cos(d), 0.0, np.sin(d)])


def observer(lat_deg, lst_hr):
    """Observer position and local ENU basis, for local solar time lst_hr."""
    lon = (lst_hr - 12.0) * 15.0 * DEG
    lat = lat_deg * DEG
    up = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    east = np.cross([0.0, 0.0, 1.0], up)
    east /= np.linalg.norm(east)
    north = np.cross(up, east)
    return R_E * up, up, east, north


def sun_elevation(lat_deg, lst_hr, dec_deg=0.0):
    _, up, _, _ = observer(lat_deg, lst_hr)
    return np.degrees(np.arcsin(np.dot(sun_dir(dec_deg), up)))


def airmass(alt_rad):
    """Kasten & Young 1989, as used in the paper."""
    z = np.clip(90.0 - alt_rad / DEG, 0.0, 91.5)
    return 1.0 / (np.cos(z * DEG) + 0.50572 * (96.07995 - z) ** -1.6364)


# ---------------------------------------------------------- constellation
def build(n_sats, relax_deg=10.0, x_ring=True, shells=SHELLS, seed=5):
    """
    Dawn-dusk sun-synchronous X-ring across the three filed shells.

    x_ring    both the 06:00 and 18:00 node families, which tilt 8-15 deg in
              opposite senses from the terminator plane and cross near the
              poles. This is the "X" in the paper's figure 1.
    relax_deg uniform +/- jitter on the node, the paper's "relaxed" case.
              relax_deg = 0 reproduces their "tight" case.
    """
    rng = np.random.default_rng(seed)
    ltans = (18.0, 6.0) if x_ring else (18.0,)
    fams = [(alt, lt) for alt, _ in shells for lt in ltans]
    n_fam = len(fams)

    n_planes_tot = int(np.clip(round(np.sqrt(n_sats) * 1.2), n_fam, 1200))
    n_planes_tot = max(n_planes_tot, n_fam)
    per_fam = int(np.ceil(n_planes_tot / n_fam))
    per_plane = int(np.ceil(n_sats / (per_fam * n_fam)))

    node, m_vec, a_all = [], [], []
    for alt, lt in fams:
        inc = sso_inclination(alt) * DEG
        raan0 = (lt - 12.0) * 15.0
        raan = (raan0 + rng.uniform(-relax_deg, relax_deg, per_fam)) * DEG
        nd = np.stack([np.cos(raan), np.sin(raan), np.zeros(per_fam)], axis=1)
        zc = np.array([0.0, 0.0, 1.0])
        h = np.cos(inc) * zc[None, :] + np.sin(inc) * np.cross(zc[None, :], nd)
        node.append(nd)
        m_vec.append(np.cross(h, nd))
        a_all.append(np.full(per_fam, R_E + alt))

    node = np.vstack(node)
    m_vec = np.vstack(m_vec)
    a = np.concatenate(a_all)
    n_planes = node.shape[0]

    th0 = (np.linspace(0, 2 * np.pi, per_plane, endpoint=False)[None, :]
           + rng.random((n_planes, 1)) * 2 * np.pi
           + rng.normal(0, 0.3 * 2 * np.pi / per_plane, (n_planes, per_plane)))
    return dict(node=node, m=m_vec, a=a, th0=th0,
                n=np.sqrt(MU / a ** 3), total=n_planes * per_plane)


def propagate(c, t_s):
    th = c["th0"] + c["n"][:, None] * t_s
    p = (np.cos(th)[..., None] * c["node"][:, None, :]
         + np.sin(th)[..., None] * c["m"][:, None, :]) * c["a"][:, None, None]
    return p.reshape(-1, 3)


# ---------------------------------------------------------------- lighting
def sunlit(pos, s):
    """Cylindrical umbra. Solar declination enters through s."""
    along = pos @ s
    perp = np.linalg.norm(pos - along[:, None] * s[None, :], axis=1)
    return (along > 0) | (perp > R_E)


def observe(pos, r_obs, up, east, north, s, zeta=ZETA, k=K_EXT):
    """Return alt, az, range, V magnitude, sunlit mask. Boley et al. eq 2."""
    rel = pos - r_obs
    d = np.linalg.norm(rel, axis=1)
    u = rel / d[:, None]
    alt = np.arcsin(np.clip(u @ up, -1, 1))
    az = np.arctan2(u @ east, u @ north) % (2 * np.pi)

    # phase angle: Sun-satellite-observer
    cos_phi = np.clip(-(u @ s), -1.0, 1.0)
    phi = np.arccos(cos_phi)
    g = (np.pi - phi) * np.cos(phi) + np.sin(phi)          # Lambertian sphere
    inner = (2.0 * zeta / (3.0 * np.pi ** 2)) * g

    R_m = d * 1e3
    with np.errstate(divide="ignore", invalid="ignore"):
        V = (V_SUN - 2.5 * np.log10(np.maximum(inner, 1e-300))
             + 5.0 * np.log10(R_m) + k * airmass(alt))
    return alt, az, d, V, sunlit(pos, s)


# =====================================================================
# The filed configuration, from Table 1 of the SpaceX letter to the FCC
# dated 29 May 2026 (ICFS File No. SAT-LOA-20260108-00016).
#
#  Group  Altitude    Incl   Shells  Planes/shell  Sats/plane   Max sats
#    1     550-568   26-32     10        30           333         99,900
#    2     565-585    97.7     10         2         4,999         99,980
#    3     686-718      30     25        30           333        249,750
#    4     707-744    97.2     22         2         5,565        244,860
#    5     946-978      30     25        30           333        249,750
#    6    967-1002    99.4     22         2         5,770        253,880
#  TOTAL                                                       1,000,000
#
# The rows sum to 1,198,120 but the column is "Maximum Satellites per
# Group" and the TOTAL is capped at 1,000,000. Groups 2, 4 and 6 are the
# sun-synchronous ones and are 49.97% of the row sum, so the terminator
# population at the cap is 499,716. Only these three make the ring.
#
# Two planes per shell is the X-ring: the filed structure puts both node
# families at the SAME altitude, so they cross rather than nest.
# =====================================================================

SSO_GROUPS = (
    # (alt_lo, alt_hi, incl_deg, n_shells, planes_per_shell, sats_per_plane)
    (565.0,  585.0, 97.7, 10, 2, 4999),
    (707.0,  744.0, 97.2, 22, 2, 5565),
    (967.0, 1002.0, 99.4, 22, 2, 5770),
)
SSO_FILED_TOTAL = sum(s * p * n for _, _, _, s, p, n in SSO_GROUPS)   # 598,720


def build_sso(n_total, relax_deg=10.0, seed=5):
    """
    The sun-synchronous half, as filed, scaled to n_total satellites.

    Returns a list of constellation dicts (one per altitude group) because
    the groups have different satellites-per-plane and cannot share one
    th0 array. propagate() works on each element unchanged.
    """
    rng = np.random.default_rng(seed)
    scale = n_total / SSO_FILED_TOTAL
    out = []
    for lo, hi, inc_filed, n_shells, per_shell, per_plane in SSO_GROUPS:
        per = max(int(round(per_plane * scale)), 1)
        alts = np.linspace(lo, hi, n_shells)
        node, m_vec, a_all = [], [], []
        for alt in alts:
            inc = sso_inclination(alt) * DEG
            for j in range(per_shell):                 # j = 0 -> 18:00, j = 1 -> 06:00
                raan0 = 90.0 if j == 0 else -90.0
                raan = (raan0 + rng.uniform(-relax_deg, relax_deg)) * DEG
                nd = np.array([np.cos(raan), np.sin(raan), 0.0])
                zc = np.array([0.0, 0.0, 1.0])
                h = np.cos(inc) * zc + np.sin(inc) * np.cross(zc, nd)
                node.append(nd)
                m_vec.append(np.cross(h, nd))
                a_all.append(R_E + alt)
        node = np.asarray(node)
        m_vec = np.asarray(m_vec)
        a = np.asarray(a_all)
        n_planes = node.shape[0]
        th0 = (np.linspace(0, 2 * np.pi, per, endpoint=False)[None, :]
               + rng.random((n_planes, 1)) * 2 * np.pi
               + rng.normal(0, 0.3 * 2 * np.pi / per, (n_planes, per)))
        out.append(dict(node=node, m=m_vec, a=a, th0=th0,
                        n=np.sqrt(MU / a ** 3), total=n_planes * per))
    return out


def total_of(cons):
    return sum(c["total"] for c in cons)


# =====================================================================
# Second brightness model: measured Starlink Gen2 Mini, scaled to AI1.
#
# Mallama, Cole, Harrington, Hornig, Respler, Worley & Lee (2023),
# "Starlink Generation 2 Mini Satellites: Photometric Characterization",
# arXiv:2306.06657.
#
#   Phase function, brightness-mitigation mode, normalised to 1,000 km
#   (their Figure 5, least-squares quadratic):
#       V_1000 = 2.630 + 0.1065 phi - 0.0005167 phi^2      (phi in degrees)
#   Mean over all their observations: 7.87 +/- 0.09
#   Unmitigated mean:                 5.08 +/- 0.08
#   Total area: 116.03 m2  (104.96 solar arrays + 11.07 antenna panel)
#
# AI1 total area 710 m2 (600 array at 250 W/m2 + 110 m2 radiator, from the
# Starmind AI1 spec sheet), so 6.12x the area, i.e. 1.97 mag brighter.
#
# IMPORTANT CAVEAT, stated by Mallama in section 1: the Gen2 Mini mitigation
# is TWO things, an improved reflective layer AND "they adjust the attitude
# of the solar arrays to minimize brightness when near the Earth's
# terminator." AI1 cannot do the second. Its arrays are power-constrained
# face-on and it lives on the terminator permanently. So an unknown part of
# the 2.79 mag of Mini mitigation does not transfer, and this model is a
# FLOOR, not a prediction.
#
# Also not modelled: specular glints off 600 m2 of flat array. Those only
# push upward.
# =====================================================================

MINI_PHASE = (2.630, 0.1065, -0.0005167)     # Mallama 2023 Fig 5, mitigated
MINI_MEAN_MIT = 7.87                          # their Table 2
MINI_MEAN_UNMIT = 5.08
MINI_AREA = 116.03
AI1_AREA = 710.0
AI1_DELTA_MAG = 2.5 * np.log10(AI1_AREA / MINI_AREA)     # 1.97


def mini_v1000(phi_deg):
    """Measured Gen2 Mini magnitude at 1,000 km, mitigation mode."""
    c0, c1, c2 = MINI_PHASE
    return c0 + c1 * phi_deg + c2 * phi_deg ** 2


def observe_empirical(pos, r_obs, up, east, north, s, mode="mitigated", k=K_EXT):
    """
    AI1 brightness anchored to measured Starlink Gen2 Mini photometry.

    mode "mitigated"   phase function, SpaceX's best demonstrated result
    mode "unmitigated" flat 5.08, what the same hardware does without it
    """
    rel = pos - r_obs
    d = np.linalg.norm(rel, axis=1)
    u = rel / d[:, None]
    alt = np.arcsin(np.clip(u @ up, -1, 1))
    az = np.arctan2(u @ east, u @ north) % (2 * np.pi)

    phi = np.degrees(np.arccos(np.clip(-(u @ s), -1.0, 1.0)))
    m1000 = mini_v1000(phi) if mode == "mitigated" else np.full_like(phi, MINI_MEAN_UNMIT)
    V = (m1000 - AI1_DELTA_MAG
         + 5.0 * np.log10(d / 1000.0) + k * airmass(alt))
    return alt, az, d, V, sunlit(pos, s)
