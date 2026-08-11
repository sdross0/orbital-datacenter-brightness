# How bright could SpaceX’s proposed orbital data centers be?

Reproducible counts behind the twilight simulation. Two published brightness
models with the same 500,000 satellites, same orbits, and same viewing site. 
Only the brightness model is different.

Shane Ross, Aerospace and Ocean Engineering, Virginia Tech.

[![Ground-level simulation of the proposed orbital data-center constellation](assets/simulation-still.png)](https://youtu.be/LBZeKyh72q4)

*Illustrative ground-level rendering from Blacksburg, Virginia. Quantitative results are reported in the table below.*

## Brightness result

These are instantaneous counts of satellites above the horizon with apparent 
visual magnitude (V < 6), a conventional naked-eye threshold under dark skies.
The site is Blacksburg, Virginia (37 N latitude) at the equinox:

| epoch | unmitigated reference case | optimistic mitigated reference case | ratio |
|---|---|---|---|
| at sunset | 66,300 | 11,500 | 6x |
| +30 min | 55,100 | 6,000 | 9x |
| +60 min | 41,700 | 1,700 | 24x |
| +90 min | 28,300 | 0 | - |

Applying the same magnitude cutoff and atmospheric-extinction model, 
1,623 stars are above the horizon from the same location.

The gap between the columns is the main result. Neither column is a prediction, 
and they are not strict mathematical bounds. They are two reference cases using 
identical orbits and observing conditions. An AI1-specific magnitude and phase 
function would substantially narrow the uncertainty.

## The two models

**Boley, Lawler & Rein 2026**, [arXiv:2608.02757](https://arxiv.org/abs/2608.02757),
their equation 2. A Lambertian sphere with zeta = albedo x area = 0.2 x 800 m2.
This is the authors’ idealized unmitigated reference case. It is implemented 
unchanged in `lsm.observe`.

Original model implementation and constellation files:
https://github.com/norabolig/odc_sky_impacts


**Mallama et al. 2023**, [arXiv:2306.06657](https://arxiv.org/abs/2306.06657).
The measured on-orbit phase function of Starlink Gen2 Mini in its brightness
mitigation mode, scaled to the AI1 array area by making it 1.97 magnitudes 
brighter; AI1 (710 m2) compared to the Mini's (116 m2) gives ratio 710/116.
Implemented in `lsm.observe_empirical`.

Gen2 Mini is used because it is the latest SpaceX design for which published
on-orbit photometry was available when this repository was prepared.

**The second column is an optimistic brightness reference case, not a prediction.** 
It assumes that the measured Gen2 Mini mitigation performance transfers 
directly to a spacecraft roughly six times larger. [SpaceX states](https://starlink.com/public-files/BrightnessMitigationBestPracticesSatelliteOperators.pdf) that Gen2 
terminator tracking points the solar arrays away from the Sun and reduces 
available power by 25%. Whether AI1 can or will use the same maneuver has 
not been published. Differences in attitude, geometry, materials, and 
projected area could therefore produce a different result.

## Constellation

The constellation is constructed from the sun-synchronous groups in Table 1 
of SpaceX’s May 29, 2026 FCC supplement. The LTAN placement and RAAN spread 
are additional modeling assumptions described below.

| altitude (km) | inclination (deg) | planes | node families |
|---|---|---|---|
| 565 - 585 | 97.7 | 10 | 2 |
| 707 - 744 | 97.2 | 22 | 2 |
| 967 - 1002 | 99.4 | 22 | 2 |

500,000 satellites, the sun-synchronous half of the filed 1,000,000 cap.
Dawn-dusk orbits, LTAN 06:00 and 18:00, with a 10 degree RAAN spread, which
is the "relaxed" case in Boley et al.

**Not included:** the approximately ~30 degree inclination shells in the same 
supplement. These results therefore describe only the 500,000-satellite 
sun-synchronous component, not the complete one-million-satellite filing.

## Running it

Requires Python 3 and NumPy.

```
python3 counts.py
```

Prints the table above, with the min and max over ten minutes of orbital
phase so you can see how stable the counts are. In the 66,300-satellite case, 
the count varies by only about 20 satellites over the ten-minute interval.

## Files

| file | what it is |
|---|---|
| `lsm.py` | photometry, orbit propagation, both brightness models |
| `counts.py` | reproduces the table |
| `ASSUMPTIONS.md` | every assumption, its provenance, and what is not modeled |

The renderer that produces the video is not included. It carries texture and
star catalog assets with their own licensing, and its exposure constants are
tuned by eye for legibility. They are a presentation choice and carry no
physical meaning. The video is an illustrative rendering. The reproducible 
quantitative output of this repository is the visibility count table above.

## License

MIT for the code. Please cite the two papers above for the models, which are
theirs, not mine.
