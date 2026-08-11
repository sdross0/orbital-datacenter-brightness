# FAQ

Common questions about the twilight simulation and the two brightness models.

## Doesn't SpaceX plan to mitigate this?

Yes, and the blue column already assumes they do. It is built from the
measured on-orbit photometry of a Starlink satellite that is *currently
flying in its brightness mitigation mode*. It is not a guess about what
mitigation might achieve. It is what mitigation has already achieved on real
hardware, scaled up for the larger spacecraft.

So the blue column is not the optimistic-because-hopeful case. It is the
optimistic-because-measured case. The open question is whether that
performance transfers to a satellite roughly six times larger with a
different shape.

## Musk said the radiator is knife-edge to the Sun. Doesn't that solve it?

It helps, and it is a real design choice in the right direction. But the
same description has the solar arrays held face-on to the Sun, and the
arrays are the large area. A radiator presenting its edge contributes very
little reflecting surface either way. The array orientation is what drives
the brightness, and pointing arrays at the Sun is what a data center in
orbit has to do to make power.

## Why not use Starlink V3 data? Isn't that what AI1 is based on?

Because there isn't any. V3 has flown once, on a suborbital path with a
perigee around 43 km. It reentered in roughly 20 minutes and was never
cataloged, so nobody has measured its brightness on orbit. Gen2 Mini is the
most recent SpaceX hardware that has actually flown in a stable orbit and
been photometrically characterized, which is why it is the anchor.

## Are these visible to the naked eye, or only in a long exposure?

Naked eye. The threshold is V = 6, the conventional limit for unaided
vision at a dark site, and atmospheric extinction is applied. Nothing here
is a stacked or long-exposure astrophotograph.

## Isn't this only a twilight problem?

That is precisely what the two models disagree about, and why the last row
matters most. The blue model says yes: by 90 minutes after sunset the count
reaches zero, because the satellites have entered Earth's shadow or dropped
below the visibility threshold. The orange model says no: roughly 28,300
would still be visible at that time.

## Why do they go dark at all? I thought sun-synchronous orbits stay lit.

Only above about 1,391 km. Sun-synchronous precession tracks Earth's pole,
not the ecliptic, and Earth's axial tilt swings the shadow cone through the
orbit plane over the year. The filed altitudes, 565 to 1,002 km, are all
below that threshold, so these satellites do pass through eclipse.

## The filing says 1,000,000 satellites. Why simulate 500,000?

The 500,000 here are the sun-synchronous groups, which is roughly half the
filed cap. The remainder sit near 30 degrees inclination and are not
included. That component contributes most heavily at low and mid latitudes,
so these counts are a floor rather than a full estimate.

## Aren't there already thousands of satellites? What's different?

Scale. There are currently something on the order of 10,000 active
satellites in total. This is a single proposed constellation roughly fifty
times that number, concentrated in dawn-dusk orbits, which are exactly the
orbits that stay sunlit while the ground below is dark.

## Isn't the simulation just tuned to look alarming?

The counts are the claim, and they are reproducible from the code with
numpy alone. Both brightness models come from published papers and are
implemented unchanged. The renderer's exposure and glow settings are a
presentation choice with no physical meaning, which is why the renderer is
not included and the count script is.

## Are you against this being built?

No. The point of showing two models rather than one is that the outcome is
not determined yet. The gap between the columns is a design decision that
has not been made public. If the mitigation transfers, this is a manageable
twilight effect. That is a good outcome and it is worth knowing whether it
is the one we are getting.

## What single number would settle this?

An expected visual magnitude for AI1 with its phase function, at a stated
range and attitude. One published curve collapses the entire range in this
simulation. Everything else here is an attempt to bracket a quantity that
SpaceX already knows and has not released.

## Why Blacksburg, Virginia?

It is where I am, and at 37 degrees north it is a fairly typical
mid-latitude site. Counts increase toward higher latitudes, where
dawn-dusk orbits spend more time sunlit relative to the observer, and
decrease toward the equator.
