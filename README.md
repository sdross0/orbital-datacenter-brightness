# How bright could SpaceX’s proposed orbital data centers be?

Reproducible counts behind the twilight simulation. Two published brightness
models with the same 500,000 satellites, same orbits, abd same viewing site. 
Only the brightness model is different.

Shane Ross, Aerospace and Ocean Engineering, Virginia Tech.

## The result

These are instantaneous counts of satellites above the horizon with apparent 
visual magnitude (V < 6), a conventional naked-eye threshold under dark skies.
The site is Blacksburg, Virginia (37 N latitude) at the equinox:

| epoch | unmitigated model | optimistic mitigated model | ratio |
|---|---|---|---|
| at sunset | 66,300 | 11,500 | 6x |
| +30 min | 55,100 | 6,000 | 9x |
| +60 min | 41,700 | 1,700 | 24x |
| +90 min | 28,300 | 0 | - |

Applying the same magnitude cutoff and atmospheric-extinction model, 
approximately 1,600 stars are above the horizon from the same location.

The gap between the columns is the main result. Neither column is a prediction. 
They represent two reference cases using the same constellation and observing 
conditions. SpaceX could narrow this uncertainty by publishing the spacecraft’s 
expected magnitude and phase function.

The gap between the columns is the point. Neither number is a prediction.
They bracket a range that only SpaceX can currently narrow, because the
quantity that would settle it, the expected magnitude with its phase
function, has not been published.

## The two models

**Boley, Lawler & Rein 2026**, [arXiv:2608.02757](https://arxiv.org/abs/2608.02757),
their equation 2. A Lambertian sphere with zeta = albedo x area = 0.2 x 800 m2.
This is the authors' stated no-mitigation reference: what these satellites do
if nobody tries to darken them. Implemented unchanged in `lsm.observe`.

**Mallama et al. 2023**, [arXiv:2306.06657](https://arxiv.org/abs/2306.06657).
The measured on-orbit phase function of Starlink Gen2 Mini in its brightness
mitigation mode, scaled to the AI1 array area by making it 1.97 magnitudes 
brighter; AI1 (710 m2) compared to the Mini's (116 m2). 
Implemented in `lsm.observe_empirical`.

Gen2 Mini is used as the anchor because it is the most recent SpaceX hardware
that has actually flown and been photometrically measured. Gen2 Mini is used 
because it is the latest SpaceX design for which published on-orbit photometry
was available when this repository was prepared.

**The second column is a floor, not a prediction.** Part of the Gen2 Mini's
mitigation is a terminator attitude maneuver. The AI1 design, with a radiator
held knife-edge to the sun and arrays held face-on, does not appear able to 
perform the same maneuver without departing from its stated radiator and 
solar-array attitudes. The real answer is probably somewhere above the 
optimistic mitigation model.

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

**Not included:** the ~30 degree inclination shell in the same supplement.
That component dominates low and mid-latitude sky coverage, so these counts
are a floor in that respect too.

## Running it

Requires numpy and nothing else.

```
python3 counts.py
```

Prints the table above, with the min and max over ten minutes of orbital
phase so you can see how stable the counts are. Roughly 20 satellites out
of 66,000.

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
