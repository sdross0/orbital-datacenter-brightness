# Orbital data centers in dawn-dusk SSO: what they look like from the ground

Physically propagated, not generated.

**Current clip:** `sso_two_models.mp4` (35.7 s, 1672x940) — see Revision 3
**Current model:** `lsm.py` (`build_sso`), `ground_lsm.py`, `orbit_lsm.py`,
`outbound.py`, `assemble_full.py`
**Verification:** `verify_lsm.py` (all checks pass)

> **Read Revision 2 at the end of this file first.** It supersedes the
> constellation, the satellite count and the power figure given below.
> Only the photometry in section 1 is still current.

Everything below Appendix A is superseded. It is kept only so the history of
the errors is legible.

---

## 1. Photometry is not mine

Brightness comes from the model published in

> Boley, A. C., Lawler, S. M. & Rein, H. (2026), "Rings in the Sky: Orbital
> Data Centres and Potential Impacts to Astronomy and the Sky",
> arXiv:2608.02757

used unchanged, their equation 2:

    V = -26.77 - 2.5 log10[ (2 zeta / 3 pi^2) ((pi - phi) cos phi + sin phi) ]
        + 5 log10 R + k chi(Z)

A Lambertian sphere, phase angle `phi`, slant range `R` in metres, Kasten-Young
airmass `chi` at zenith angle `Z`. The authors' position is that this is a
**no-mitigation reference**, not a prediction: real satellites should come in
below it only to the extent operators actually mitigate.

## 2. Parameters, with provenance

| quantity | value | source |
|---|---|---|
| cross-sectional area | 800 m2 | SpaceX supplement to FCC, 29 May 2026 |
| albedo | 0.2 | Boley et al. assumption, **not** a filed value |
| zeta = albedo x area | 160 m2 | the only quantity that sets brightness |
| altitude shells | 500 / 1,000 / 2,000 km | Schedule S, SAT-LOA-20260108-00016, planes 1-3 |
| inclinations | 97.4 / 99.5 / 104.9 deg | Schedule S; sun-synchronous to 0.02 deg |
| RAAN tolerance | +/- 30 deg filed | Schedule S; render uses +/- 10, the paper's "relaxed" case |
| node families | LTAN 06:00 and 18:00 | X-ring; crossings near the poles |
| total satellites | 1,000,000 | SpaceX filing headline |
| extinction | k = 0.15 mag/airmass | Boley et al. |
| observer | Blacksburg VA, 37.23 N, LST 18:35 | sun 4.2 deg below the horizon |
| epoch | equinox, circular orbits | see section 6 on why this matters |
| star catalogue | Yale BSC cumulative counts | `stars.py`, real counts, same extinction |

## 3. Per-satellite power: what it does and does not affect

**Assumed value: 120 kW**, from Musk's description of the satellite as
"essentially an optimized Vera Rubin NVL72."

**This number does not enter the brightness calculation at all.** It appears
only in the on-screen caption ("36 MW total", "12 GW total", "120 GW total").
Setting it to 50 kW or 500 kW would render an identical sky.

That is a deliberate change from the first-pass model, where area was *derived*
from power via Stefan-Boltzmann and the solar constant, so a bad power guess
propagated straight into apparent magnitude. It is now taken from the filing
instead.

The two numbers are not fully consistent, in an informative direction. An
independent power balance at 300 K radiator temperature, emissivity 0.9,
two-sided, and 30% cells gives:

| power | area required |
|---|---|
| 120 kW | 439 m2  (145 radiator + 294 array) |
| 200 kW | 732 m2 |
| 219 kW | 801 m2 |

SpaceX filed 800 m2, which under those assumptions is a **220 kW** satellite,
not a 120 kW one. Either the radiators run cooler than 300 K, the cells are
worse than 30%, there is margin, or the machine is closer to 200 kW than the
NVL72 analogy suggests.

**Consequence for captions:** the area is filed and defensible. The power is
inference, and the gigawatt total is inference layered on inference. Prefer
"800 m2 each, per the FCC filing" over any GW figure in public material.

**Legacy value:** `Scenario.power_MW = 100.0` still sits in `sso_datacenter.py`,
and `scaleup.py` uses 100 MW / 1 MW. Neither feeds the current clip. They are
dead defaults from the first week, before the NVL72 comment.

## 4. Results

Blacksburg, equinox, sun 4.2 deg below the horizon, looking away from the
sunset. Naked-eye limit V < 6, extinction applied identically to stars and
satellites.

Above the horizon and sunlit at that instant, out of 1,000,000: **164,028**.
That figure is pure orbital geometry and does not depend on any brightness
assumption.

| satellites filed | visible to the eye | vs 1,612 stars |
|---|---|---|
| 300 | 40 | 0.03x |
| 100,000 | 13,576 | 8.4x |
| 1,000,000 | 133,335 | 82.7x |

Boley et al. conclude "about 100 times more visible satellites in the night sky
than visible stars." Same order, from a different constellation build.

### Sensitivity to the brightness model

The conclusion is far more robust than the model. Applying a uniform dimming
to every satellite:

| dimming | visible V<6 | vs stars |
|---|---|---|
| none | 133,335 | 82.7x |
| 1 mag | 108,320 | 67.2x |
| 2 mag | 80,949 | 50.2x |
| 3 mag | 51,740 | 32.1x |
| 4 mag | 24,693 | 15.3x |
| 5 mag | 9,886 | 6.1x |
| 6 mag | 2,668 | 1.7x |
| 7 mag | 239 | 0.1x |

Parity with the stars requires about **6.4 magnitudes**, a factor of 347 in
reflected light, on a satellite with 800 m2 of surface. The best mitigation
Starlink has demonstrated is roughly 3 magnitudes on a satellite forty times
smaller.

Against the IAU recommendation of V > 7 + 2.5 log10(altitude / 550 km):
**1.4%** of the shell complies as modelled, median shortfall 4.7 mag.

Light pollution makes the ratio worse, not better. At V < 5, roughly a suburban
sky, it is 108,320 satellites against 515 stars, or 210 to 1. City light erases
faint stars faster than it erases these.

## 5. Verification

`verify_lsm.py`, all passing:

| check | result |
|---|---|
| sun-synchronous inclinations vs filed Schedule S | 97.40 / 99.48 / 104.89 vs 97.4 / 99.5 / 104.9 |
| Lambertian sphere magnitude, closed form | V = -1.372 at phi=0, R=700 km |
| range scaling | 5 log10(2) exactly |
| V < 0 count vs paper Table 1 | 5,108 vs their 5,100 |
| stars V < 5 vs paper | 515 vs ~500 |
| stars V < 6 vs paper | 1,612 vs ~1,700 |
| eclipse threshold, Boley eq 3 fixed point | 1,391 km |
| eclipse threshold, beta angle route | 1,391 km |

Counts fainter than V=5 run high against their Table 1 (138,000 vs 98,000).
Expected: their 1,000,000 is split between the X-ring **and** a ~30 degree
inclination shell, while this build puts the whole million in the rings. The
V < 0 agreement, which is insensitive to the altitude distribution, is the
check that actually tests the photometry.

## 6. Corrections to claims made publicly

### 6a. "Nothing is eclipsed" — wrong below 1,400 km

Earlier versions of this document and my public posts stated that a dawn-dusk
sun-synchronous shell never enters Earth's shadow. That holds only above about
1,391 km. Sun-synchronous precession tracks Earth's **pole**, not the ecliptic,
so the 23.44 deg obliquity tilts the shadow cone relative to the orbit plane and
each ring acquires an eclipse season near one solstice.

Two independent derivations agree to the kilometre: Boley et al.'s equation 3
fixed point, and a beta-angle test against Earth's angular radius. Both give
1,391 km. Two of the three filed shells are below it.

At 700 km the shell is eclipsed whenever solar declination exceeds 17.5 deg,
roughly early May to early August for a dusk node, costing about 19 minutes of
each 98.6 minute orbit.

**But it matters less to the ground view than that sounds.** The eclipsed arc is
centred on the anti-solar direction, so at the eclipsing solstice it sits over
the opposite hemisphere from a dusk observer at mid-northern latitude. All
renders are at equinox, where no shell is eclipsed at any altitude.

This also undercuts the perpetual-sunlight argument *for* orbital data centres,
which is a bigger deal than anything in the video.

### 6b. The brightness calibration ran the wrong way

Earlier renders anchored to measured Starlink photometry (Mallama et al.),
applying a +3.6 mag offset calibrated against VisorSat. That offset absorbs the
*mitigation* Starlink achieves with visors and dark coatings, and also absorbs
the area difference between a Starlink and an ODC. Applying it to a satellite
forty times larger silently assumes ODC operators achieve VisorSat-grade
mitigation. Nobody has committed to that.

| version | effective albedo x area |
|---|---|
| earlier render, raw | 0.10 x 439 m2 = 43.9 m2 |
| earlier render, calibrated | after +3.6 mag = 1.59 m2 |
| Boley et al. reference | 0.20 x 800 m2 = 160 m2 |

The calibrated version was **5.0 magnitudes dimmer** than the published
reference, not brighter. The uncalibrated version was still 1.4 mag dimmer. The
public correction I was preparing was pointed in the wrong direction.

### 6c. Albedo 0.6 was wrong

Optical solar reflectors are bright, but the sun-facing surface here is
predominantly solar array, which is dark. 0.6 was indefensible. The current
model uses the paper's 0.2 on the full 800 m2 cross-section.

## 7. Not modelled

- **The ~30 degree inclination shell** from the May 2026 supplement. Boley et al.
  find this component dominates low and mid-latitude sky cover. Counts here are
  therefore a **floor**, not an estimate.
- **Specular glints.** Diffuse only. Real flat radiators and arrays flare far
  brighter for brief windows. Another reason these are a floor.
- **Diffuse sky background.** Individual point sources only. Hainaut (2026)
  shows aggregate scattered light spreads the impact well beyond the ring.

- **Star positions, in the counting scripts.** `stars.py` reproduces the real
  magnitude distribution from the catalogue tabulation but scatters stars at
  random, with a fabricated Milky Way. That is harmless for counting, which
  depends only on the distribution, and wrong for pictures. The renderer uses
  `realstars.py` instead: 8,913 real stars brighter than V = 6.5 from the HYG
  database, with true positions and B-V colour.

- **Twilight sky brightness, in the headline table.** The counts in `counts.py`
  apply V < 6 at every epoch. That is a *dark-sky* naked-eye threshold, and at
  sunset the sky is nowhere near dark, so those early-epoch counts credit the
  satellites with a detection limit the sky does not permit. Raised by
  @Obserfessor on X, and correct.

  `twilight.py` and `counts_twilight.py` apply an epoch-dependent limit
  instead. Two steps, and the sources matter:

  - Zenith sky brightness against solar elevation, from the piecewise fit by
    Han Kleijn (2017), hnsky.org/sqm_twilight.htm, made from his Unihedron
    SQM-L measurements plus published ESO twilight photometry. Cited as
    Kleijn rather than the underlying ESO work, because it is his fit that
    is implemented here.
  - Naked-eye limiting magnitude from that brightness, using Olof Carlin's
    inversion of Schaefer (1990), PASP 102, 212, in the form implemented in
    K. Fisher's Unihedron conversion calculator.

  **Known passband inconsistency.** Carlin's relation maps a B-band surface
  brightness to a V-band point-source limit, while the twilight fit is
  anchored to broadband SQM-L and V-band data. The mismatch is worth a few
  tenths of a magnitude and has not been reconciled. From `sensitivity.py`,
  0.1 mag moves the mitigated count by about 11 percent and the unmitigated
  one by 0.7 percent, so this is a real uncertainty on the blue column and a
  negligible one on the orange. The correction is large and it moves the result
  rather than shrinking it:

  | after sunset | sun el | V limit | unmitigated | mitigated | stars |
  |---|---|---|---|---|---|
  | 0 min | 0.0 | -6.90 | 0 | 0 | 0 |
  | 30 min | -6.0 | -0.64 | 151 | 0 | 1 |
  | 60 min | -11.9 | 5.01 | 33,496 | 0 | 536 |
  | 68 min | -13.4 | 5.86 | 37,656 | 515 | 1,395 |
  | 90 min | -17.7 | 6.49 | 32,310 | 720 | 2,868 |
  | 120 min | -23.5 | 6.48 | 18,569 | 0 | 2,831 |

  Nothing is visible in either case for roughly the first 25 minutes. The
  unmitigated count peaks near 68 minutes after sunset, not at sunset, and the
  mitigated count never exceeds about 1,300, which is fewer than the stars
  visible at the same moment.

  Still approximate. The sky-brightness fit is for the **zenith**. Naked-eye
  limits also vary substantially between observers, and the Schaefer relation
  is itself an approximation.

  **Boley et al. did not make this mistake.** Their paper gates on solar
  depression (counts shown only once the Sun is 6 degrees or more below the
  horizon), uses V < 5 rather than V < 6, and includes only satellites more
  than 10 degrees above the horizon. All three guards were dropped in adapting
  their model here, not by them. `counts_twilight.py` now reports their
  conventions alongside:

  | after sunset | this work | Boley conventions |
  |---|---|---|
  | 60 min | 33,496 | 26,923 |
  | 68 min | 37,656 | 24,447 |
  | 90 min | 32,310 | 15,741 |
  | 120 min | 18,569 | 8,051 |

  Under their conventions the mitigated case is **zero at every epoch**,
  because the brightest mitigated satellite anywhere in the constellation is
  V = 5.37, fainter than their V < 5 cut.

- **Artificial skyglow.** The counts assume a naturally dark site. Blacksburg
  is a town of 45,000 and is not one. `twilight.py` now takes an artificial
  skyglow term by Bortle class. At the unmitigated peak, satellites above 10
  degrees:

  | site | naked-eye limit | unmitigated | mitigated | stars | ratio |
  |---|---|---|---|---|---|
  | pristine, Bortle 1 | 5.89 | 27,567 | 550 | 1,394 | 20:1 |
  | rural, Bortle 3 | 5.64 | 26,784 | 191 | 1,052 | 25:1 |
  | rural/suburban, Bortle 4 | 5.46 | 26,036 | 36 | 872 | 30:1 |
  | suburban, Bortle 5 | 5.06 | 24,557 | 0 | 553 | 44:1 |
  | city, Bortle 8 | 3.49 | 13,995 | 0 | 94 | 149:1 |

  Skyglow separates the two cases rather than blurring them: it erases the
  faint mitigated satellites entirely while the bright unmitigated ones
  survive, and it removes stars faster than either. Kyba et al. (2023),
  Science 379, 265, find skyglow rising 9.6 %/yr, equivalent to the naked-eye
  limit falling 0.044 mag/yr, which pushes the ratio the same way over time.
  Extrapolating that rate across decades is speculative.

- **Camera azimuth in the video.** Fixed at 315 degrees, northwest, HFOV 95.
  Chosen by scanning heading against the number of satellites clearing the
  local sky limit, summed over the evening. Northwest wins because the
  dawn-dusk ring hugs the terminator, so it has to be looked for toward the
  sunset. Looking east is nearly empty: the darkest sky is anti-solar, and
  satellites there are in Earth's shadow. Totals across the evening were
  29,883 at 315 deg, 24,984 at 240 deg, 20,925 at 0 deg and about 20 anywhere
  between 60 and 120 deg.

- **Sky background in the render.** Now radiometric, in `skymodel.py`. The
  measured zenith brightness from `twilight.py` is spread over the dome by
  three terms: residual twilight brightening toward the Sun, which fades to
  nothing by the end of astronomical twilight; an airglow term using the van
  Rhijn path length through a 90 km layer, attenuated by extinction along the
  same path, which peaks near 12 deg elevation and leaves the horizon itself
  about 0.8 mag darker than the zenith; and Earth's shadow with the Belt of
  Venus above it in the anti-solar direction.

  Only the zenith is anchored to data. The angular shape is empirical and
  chosen to look right, which is why the counts still quote the zenith value:
  the frame is the illustration, the counts are the claim.

  With the sky carrying real units, a satellite is drawn only if it beats the
  local sky at its own position, so the number on screen and the picture beside
  it agree by construction rather than by assertion.
- **Orbit raising and lowering.** The paper estimates ~7% of satellites are off
  their operational altitude at any time, at unknown and probably higher
  brightness.
- **Tumbling failures.** ~1% Starlink on-orbit failure rate implies frequent
  very bright glints from 800 m2 of uncontrolled surface.
- Spherical Earth, circular orbits, cylindrical umbra, equal population split
  across the three shells (the filing gives no split).

## 8. Rendering notes

**Ground act.** 10x real time, labelled on screen. Brightest 300 sources get
individual PSF stamps; the remainder are splatted and FFT-convolved with the
same kernel, so both paths are linear superpositions of one profile. Stars and
satellites go through an identical magnitude to flux to PSF path, which is what
makes the on-screen count comparison honest.

**Orbit act.** The **same 500,000 satellites** as the ground act, not a reduced
sketch, so nothing changes at the handoff except the vantage point. Same
ephemeris viewed from a ray-traced Earth. Motion runs at 240x easing to 10x
through the dive, integrated *backwards* from the handoff so the last dive frame
lands exactly on the ground clip's t = 0. Satellites behind Earth are hidden by
line-of-sight sphere intersection. Brightness is the Boley Lambertian sphere
model throughout, at a fixed print exposure. Rendering uses the same two-path
scheme as the ground act: the brightest 400 sources get individual PSF stamps,
the remainder are splatted and FFT-convolved. 28-frame dissolve to the ground
plate.

**The globe.** Coastlines are real, from `global-land-mask` (~1 km). Surface
colour, cloud cover and sea ice are synthesised from climate bands plus fractal
noise. Geography true, appearance invented. No city lights, because inventing
those would put fake information in the part of the frame a viewer reads as data.

**Foreground.** From the supplied twilight plate. The sky gradient (Earth's
shadow plus Belt of Venus) is synthesised for the anti-solar view.

---

# Appendix A: superseded first-pass model

Kept for provenance. **Do not cite any number in this appendix.** Every
quantity here is wrong in at least one of the ways documented in section 6.

| Quantity | Value then | Why it is wrong |
|---|---|---|
| Altitude | 700 km, band 700-1000 | filing lists 500 / 1,000 / 2,000 |
| Per-satellite power | 100 MW | off by ~3 orders; also should not drive brightness |
| Albedo | 0.60 | see 6c |
| Total area | 3.66e5 m2, 605 m a side | consequence of the 100 MW error |
| Brightest satellite | mag -8.1 | consequence of the above |
| "Nothing is eclipsed" | asserted | see 6a |
| Star field | decorative, not a catalogue | now real Yale BSC counts |
| Filed population | quoted as 480,000 | filing headline is 1,000,000 |

Photometry then was a Lambertian flat panel held normal to the Sun,

    E_obs / E_sun = rho A cos(i) cos(e) / (pi d^2)

which is a defensible functional form. The failure was in the inputs, not the
optics.

Superseded files: `sso_datacenter.py` (still holds `power_MW = 100.0` as a dead
default), `scaleup.py`, `calibrated.py`, `vertical.py`, `dense.py` (its
`observe()` is unused by the current path; its splat and FFT helpers are still
used).

---

# Revision 2, 7 August 2026: the filed configuration

Supersedes everything above except the Boley/Lawler/Rein photometry, which is
unchanged. Current clip: `sso_odc_500k_landscape.mp4` (37.8 s, 1672x940).

## What changed

The previous render put all 1,000,000 satellites in sun-synchronous orbit.
That was wrong. Table 1 of the SpaceX letter to the FCC dated 29 May 2026
(ICFS File No. SAT-LOA-20260108-00016) splits the constellation:

| Group | Altitude | Incl | Shells | Planes/shell | Sats/plane | Max sats |
|---|---|---|---|---|---|---|
| 1 | 550-568 km | 26-32 | 10 | 30 | 333 | 99,900 |
| 2 | 565-585 km | 97.7 | 10 | 2 | 4,999 | 99,980 |
| 3 | 686-718 km | 30 | 25 | 30 | 333 | 249,750 |
| 4 | 707-744 km | 97.2 | 22 | 2 | 5,565 | 244,860 |
| 5 | 946-978 km | 30 | 25 | 30 | 333 | 249,750 |
| 6 | 967-1002 km | 99.4 | 22 | 2 | 5,770 | 253,880 |
| TOTAL | | | | | | 1,000,000 |

The rows sum to 1,198,120 while the TOTAL says 1,000,000. This is not an
error: the column is "**Maximum** Satellites per Group," so the per-group
figures are ceilings and the total is a cap. Groups 2, 4 and 6 are the
sun-synchronous ones and are 49.97% of the row sum, so the terminator
population at the cap is 499,716. **Only those three make the ring.**

The 30-degree groups are still not modelled. They contribute at low and mid
latitudes but not to the ring structure, so these counts remain a floor.

## Structural consequence

Two planes per shell means the X-ring puts **both node families at the same
altitude**. They cross rather than nest. Closing speeds at the crossings are
13 to 15 km/s. Boley's parenthetical about alternating nodes by altitude to
prevent ring intersections describes Blue Origin's Sunrise, which uses one
plane per shell. It does not describe SXODC.

With roughly 4,600 satellites per plane and only 108 planes, adjacent
satellites in a plane sit about 9.7 km apart, subtending half a degree at
typical slant range. That is why the render shows strings of beads rather
than a smooth band. The Schedule S specifies "Evenly-Spaced."

## Parameters

Unchanged from Revision 1: zeta = 0.2 x 800 m2, k = 0.15, Kasten-Young
airmass, Lambertian sphere per Boley et al. eq 2, observer at Blacksburg
37.23 N, LST 18:35, equinox, sun 4.2 deg below the horizon.

Per-satellite power is now **175 kW**, from Michael Kan (PCMag), replacing my
own 120 kW inference from Vera Rubin NVL72 rack draw. Musk described the
satellite as "essentially an optimized Vera Rubin NVL72 computer" but gave no
wattage; the 120 kW was mine, not his. Power appears only in the caption and
does not enter the photometry.

175 kW cross-checks against the filing: 800 m2 total minus 100 m2 of bus and
radiator leaves ~700 m2 of array, and 175 kW from that is 18.4% efficiency,
matching the "lightweight, flexible thin-film photovoltaic materials" the same
letter describes.

## Open question, not resolved

The same table lists Total Area 800 m2, Mass 3,000 kg, and Area-to-Mass
0.1333 m2/kg. But 800/3000 = 0.2667. The 0.1333 figure implies **400 m2**,
suggesting 800 m2 is one-sided physical area and 400 m2 is the average
projected cross-section.

Boley et al. take 800 m2 as the sphere cross-section. If 400 is correct,
every magnitude here is 0.75 too bright. This render uses 800 to stay
consistent with the published model. Query sent to the authors.

## Other filed numbers now on record

- Mass 3,000 kg each. At a 5-year life and the full million, that is 200,000
  reentries per year and 600,000 tonnes, 15 to 40 times the natural meteoric
  influx. My earlier public figure of 200,000 tonnes assumed 1 tonne and was
  3x low.
- 100 m2 of bus and radiator. Rejecting 175 kW from that area two-sided
  requires a radiator near 362 K (89 C). Radiator area is set by
  Stefan-Boltzmann, but temperature is the escape hatch and they are using it.
- SpaceX requests a waiver to dispose of satellites between 600 and 2,000 km
  into high-altitude Earth or heliocentric orbits rather than by reentry.
  Escape from these altitudes costs about 3.0 to 3.1 km/s and a 2,500 km
  graveyard about 0.65 to 0.86 km/s, against the 50 m/s they reserve.
- Passive decay time 1.2 to 1.9 years for the 550-585 km shells.

## Result

| satellites | above horizon | visible V<6 | vs 1,612 stars |
|---|---|---|---|
| 300 | 42 | 34 | 0.02x |
| 50,000 | 7,032 | 5,888 | 3.7x |
| 500,000 | 71,969 | 60,073 | 37.3x |

Every sun-synchronous group is below the 1,391 km threshold for year-round
illumination, so none achieves the perpetual sunlight that motivates the
orbit. 565 km needs 1,070; 1,002 km needs 1,221.

---

# Revision 3, 8 August 2026: two brightness models side by side

Clip: `sso_two_models.mp4` (35.7 s). Code: `compare.py`, `assemble_compare.py`.
Verification: `verify_cmp.py`, all passing.

Constellation unchanged from Revision 2: the three sun-synchronous groups of
SpaceX's filed Table 1, 500,000 satellites, X-ring, filed plane structure.

## Why two models

Revision 2 used only the Boley/Lawler/Rein Lambertian sphere. Their paper
states that this is a **no-mitigation reference**, not a prediction. It has
no attitude and does not know that SpaceX mitigates. Presenting it alone
overstates what is likely.

The second model is empirical. Mallama, Cole, Harrington, Hornig, Respler,
Worley & Lee (2023), arXiv:2306.06657, measured Starlink Gen2 Mini in
brightness mitigation mode and published a phase function, their Figure 5:

    V_1000 = 2.630 + 0.1065 phi - 0.0005167 phi^2      (phi in degrees)

Their mean over all observations is 7.87 +/- 0.09; unmitigated is 5.08. Total
Mini area is 116.03 m2 (104.96 arrays + 11.07 antenna panel), their section 2.

AI1 is 710 m2 (600 m2 array at 250 W/m2 plus a 110 m2 radiator, Starmind AI1
spec sheet), so 6.12x the area, 1.97 magnitudes brighter. Range and
Kasten-Young extinction are then applied per satellite from the propagator.

| model | AI1 at 1,000 km |
|---|---|
| Boley et al., Lambertian sphere | -0.60 at full phase, +0.65 at 90 deg |
| Mallama phase function, scaled | 4.60 at full phase, 6.06 at 90 deg |

## Result

Blacksburg, equinox, looking SSW, whole sky, V < 6, against 1,612 stars:

| epoch | sun elevation | Boley | Mallama-anchored | ratio |
|---|---|---|---|---|
| sunset | 0.0 | 66,316 | 11,517 | 5.8x |
| +30 min | -6.0 | 55,082 | 5,976 | 9.2x |
| +60 min | -11.9 | 41,730 | 1,712 | 24.4x |
| +90 min | -17.7 | 28,333 | 0 | - |

The two models agree within a factor of six at sunset and disagree completely
by ninety minutes, where one shows an arc and the other shows nothing. That
divergence is the finding. Nobody has flown an AI1, so neither column can be
confirmed.

## Three caveats stated on screen or in the description

**The empirical model is a floor, not a prediction.** Mallama's section 1
says the Gen2 Mini mitigation is two things: an improved reflective layer,
*and* "they adjust the attitude of the solar arrays to minimize brightness
when near the Earth's terminator." AI1 cannot do the second. Its arrays are
power-constrained face-on and it lives on the terminator permanently. An
unknown share of the 2.79 magnitudes of Mini mitigation therefore does not
transfer.

**Specular glints are not modelled.** 600 m2 of flat array will produce
mirror reflections that are invisible from almost everywhere and very bright
from one direction. With 500,000 satellites, someone is always in that cone.
Diffuse-only models cannot see this, and it only pushes upward.

**The satellite count above the horizon is pure geometry.** 74,375 of the
500,000 are above the horizon and sunlit at sunset. That figure does not
depend on either brightness model.

## What is NOT in SpaceX's filings

The January narrative (SAT-LOA-20260108-00016) contains two sentences on the
subject: SpaceX will preserve astronomy "including by developing
industry-leading brightness mitigations." No magnitude target, no coating, no
attitude policy, no verification method. The 29 May supplement contains no
mention of brightness at all. Boley et al. note in their introduction that
operators who once committed to a magnitude 7 threshold have since moved away
from it.

So the mitigated column is being generous: it holds SpaceX to their own best
demonstrated result on hardware they were careful with, which is more than
they have committed to.

## Camera

Fixed azimuth 200 degrees, south-southwest, HFOV 95. Chosen because the ring
sweeps from due south at sunset toward the northwest, and a fixed SSW camera
keeps it in frame across all four epochs. Panning to follow the ring would
have been easier to look at and less honest. The frame shows roughly a sixth
of the sky; the counters report the whole sky.

# Revision 4, 16 August 2026: the season, and two model bugs

Building an interactive version of the simulation, which lets anyone pick a
latitude, date and time rather than fixing them at Blacksburg and an equinox,
turned up one substantive result and two defects in the sky model. All three
are recorded here because two of them change published claims.

## 4.1 The seasonal swing is the largest effect in this repository

Every earlier table is for an equinox. The equinox turns out to sit close to
the quietest point of the year for the mitigated case, so quoting it alone
was misleading.

Whole sky, 37.2 N, dark site, each model at its own peak:

| date | unmitigated | mitigated | stars | mitigated / stars |
|---|---|---|---|---|
| Mar equinox | 37,568 | 1,334 | 2,527 | 0.5 |
| Jun solstice | 759 | 0 | 917 | 0 |
| Sep equinox | 37,803 | 1,401 | 2,376 | 0.6 |
| Dec solstice | 62,272 | 13,745 | 2,602 | 5.3 |

Between about 13 April and 30 August the mitigated case never becomes visible
at all at this latitude, and the transition at each end takes under two weeks:
258 satellites on 2 April, 69 on 8 April, zero by 14 April. From October
through February it exceeds the stars, by about five to one at the solstice,
and stays visible for close to three hours instead of forty minutes.
Reproduce with `seasonal.py`.

**Mechanism.** A dawn-dusk sun-synchronous orbit is fixed relative to the
day-night line but not relative to the Sun's declination, so the
Sun-satellite-observer phase angle swings through the year. Over the satellites
actually visible at each peak:

| date | minimum phase | median phase |
|---|---|---|
| Sep equinox | 94 deg | 122 deg |
| Dec solstice | 11 deg | 55 deg |

The Mallama Gen2 Mini phase function is 3.64 mag at 10 degrees and 8.03 mag at
90, a factor of about 58 in flux, so a constellation seen at solstice geometry
is being lit in the part of the curve where it is dramatically brighter. The
Lambertian sphere of Boley et al. has a much weaker phase dependence, which is
why the two columns move by very different factors across the year.

**What this changes.** The claim that the optimistic mitigated case never
approaches the star count, made in earlier versions of the README and in the
11 August LinkedIn post, is true at an equinox and false for roughly half the
year. It has been corrected in the README.

**What it does not change.** Nothing in the unmitigated column, and nothing
about the equinox figures themselves, which remain correct for their date.

## 4.2 Earth's shadow and the Belt of Venus never faded (skymodel.py)

`skymodel.brightness` applied the solar glow term with a twilight factor that
reaches zero when the Sun is 18 degrees down, but applied the Earth-shadow
darkening and the Belt of Venus brightening with no such factor. Two hours
after sunset, with the Sun 22 degrees down, the model still drew a shadow edge
and a bright rim above it near 60 degrees altitude, with a pink tint from the
matching term in `colour`.

This is wrong for a physical reason, not just a cosmetic one: the shadow and
the belt are visible only because there is sunlit air to cast a shadow on.
Past the end of astronomical twilight the whole sky is inside the shadow.
Both terms now carry the same twilight factor as the glow.

**Effect on published results: none that is measurable.** Both terms act only
in the anti-solar sky, weighted by `clip((theta - 90) / 60, 0, 1)`. The
published video faces northwest, toward the Sun's side, where that weight
reaches at most 0.185 across the frame. Recomputing the video's on-screen
counts with and without the fix moves them by 0 to 0.3 percent. Pointed east
the error would have been obvious, which is luck rather than care. The
whole-sky counts never used this module at all: they take sky brightness from
`twilight.py`, at the zenith.

## 4.3 The renderer ignored the Sun's declination (frame.py)

`frame.sun_altaz` and `frame.render` both called `L.sun_dir(0.0)`, hard-coding
an equinox, while `frame.DEC` was set by callers and never read. Any rendered
frame for a date away from an equinox therefore used equinox lighting for both
the sky brightness and the satellite illumination.

**Effect on published results: none.** The video is a September equinox
render, where the true declination is 0.005 degrees. Every seasonal figure in
section 4.1 comes from `peak_minutes` and `whole_sky_count`, which compute
their own solar position and were never affected.

`DEC` now defaults to 0.0 at module level, so the video pipeline is unchanged.

## 4.4 Star counts were about ten percent high

Earlier tables counted stars from the isotropic synthetic sky in `stars.py`,
which spreads the standard whole-sky tabulation evenly over the hemisphere.
Counting real stars from the HYG catalogue at the actual date and latitude
gives about ten percent fewer above the horizon: 2,565 rather than 2,831 at
full dark from Blacksburg at the equinox. `counts_twilight.py` now uses the
catalogue. No satellite number depends on this.

## 4.5 Limitations the interactive version adds

- **Artificial skyglow across the dome.** The Bortle setting is a zenith value
  carried outward with the same geometry as airglow. A real light dome is not
  axisymmetric; it points at whatever town is nearest. Treat the Bortle
  control as indicative.
- **The panorama is a storage format.** The whole sky is rendered in altitude
  and azimuth and reprojected to a correct perspective view in the browser.
  The reprojection was checked against `frame.py` and agrees to better than a
  third of a pixel, but the panorama's own resolution, about 11 pixels per
  degree at the standard setting, sets the sharpness of what you see.
- **Counts shown in the viewer are sampled.** The figure that follows the view
  as you drag comes from a thinned sample of the visible satellites, scaled
  back up. It carries sampling noise at small numbers. The whole-sky figures
  beside the picture are exact.
