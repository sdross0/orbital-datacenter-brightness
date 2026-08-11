# How bright would SpaceX's orbital data centers be?

Reproducible counts behind the twilight simulation. Two published brightness
models, the same 500,000 satellites, the same sky. Only the model changes.

Shane Ross, Aerospace and Ocean Engineering, Virginia Tech.

## The result

Satellites above the horizon and brighter than V = 6, so visible to the
unaided eye, from Blacksburg Virginia at the equinox:

| epoch | Boley no-mitigation | Mallama-anchored | ratio |
|---|---|---|---|
| at sunset | 66,300 | 11,500 | 6x |
| +30 min | 55,100 | 6,000 | 9x |
| +60 min | 41,700 | 1,700 | 24x |
| +90 min | 28,300 | 0 | - |

For scale, 1,612 stars are visible to the unaided eye from the same site.

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
mitigation mode, offset by +1.97 mag for the ratio of the AI1 array area
(710 m2) to the Mini's (116 m2). Implemented in `lsm.observe_empirical`.

Gen2 Mini is used as the anchor because it is the most recent SpaceX hardware
that has actually flown and been photometrically measured. V3 has flown once,
on a suborbital path, and was never cataloged, so no photometry exists for it.

**The second column is a floor, not a prediction.** Part of the Gen2 Mini's
mitigation is a terminator attitude maneuver. The AI1 design, with a radiator
held knife-edge to the sun and arrays held face-on, structurally cannot
perform it. The real answer is somewhere above the blue column.

## Constellation

The sun-synchronous groups exactly as filed, from Table 1 of SpaceX's
29 May 2026 supplement to the FCC:

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
physical meaning. The counts above are the claim, and they are what is
reproducible here.

## Corrections to earlier versions

<!-- SHANE: replace this block before making the repo public. Be specific,
     one line per item, with what was wrong and what it is now. Being precise
     about your own errors is what makes the rest of this trustworthy. -->

- The earlier render used my own brightness assumption rather than a
  published model. It is now Boley et al. eq 2, unchanged.
- The earlier render used a simplified constellation geometry rather than
  the groups as filed. It now uses Table 1 of the 29 May supplement.
- I stated that Starlink V3 was in orbit. It has flown once on a suborbital
  path and reentered. Corrected by Jonathan McDowell.

## License

MIT for the code. Please cite the two papers above for the models, which are
theirs, not mine.
