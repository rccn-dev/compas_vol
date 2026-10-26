"""Processes that produce a field from nothing.

Neither of these starts from a shape. They start from a disturbance, and the
pattern is what the physics settles into -- which is the point: you choose a
feature size and a volume fraction rather than drawing a structure.
"""

import numpy as np

from .field import Field

__all__ = ["spinodal", "reaction_diffusion"]


def spinodal(bounds, resolution=128, feature=8.0, fraction=0.45, steps=400, mobility=1.0, dt=0.8, seed=1):
    """Phase separation: a bicontinuous foam, by Cahn-Hilliard.

    A mixture that is unstable everywhere separates into two phases at once,
    and both stay connected while they coarsen. It is how bicontinuous
    polymer blends, porous glasses and nanoporous metals actually form, and
    what it gives you here is a TPMS with the periodicity taken out:
    isotropic, aperiodic, no unit cell, no preferred direction, both the solid
    and the void continuous throughout.

    The equation is stiff, so it is solved in Fourier space with the linear
    part implicit, on the voxel lattice rather than in millimetres -- in
    physical units the coefficients would have to be re-derived for every
    resolution. ``feature`` is converted for you.

    Parameters
    ----------
    bounds : :class:`compas.geometry.Box` | float | sequence
        The domain. The result fills it and is periodic across its faces,
        which is what makes it tile.
    resolution : int | tuple[int, int, int]
    feature : float
        Wall thickness and pore size, in mm, at the point separation ends.
        Structure coarsens as ``steps`` grows, so the two interact.
    fraction : float
        Solid fraction, in ``(0, 1)``, and it is exact: the surface is taken
        at whichever contour of the separated mixture holds that share. The
        dynamics decide the morphology, the level decides how much of it is
        solid, and separating those two makes the parameter dependable --
        left to the dynamics alone it lands several points low, because the
        phases are still saturating. Below about 0.3 the solid stops
        percolating and falls into islands.
    steps : int
        Separation is quick; coarsening is slow. A few hundred steps is
        separated and fine, a few thousand is coarse and smooth.
    mobility, dt : float
        Numerics. Raise ``dt`` to coarsen faster, at the risk of instability.
    seed : int

    Returns
    -------
    :class:`compas_vol.processes.Field`

    Examples
    --------
    >>> from compas_vol.processes import spinodal
    >>> foam = spinodal(bounds=20.0, resolution=32, feature=6.0, steps=60, seed=0)
    >>> 0.2 < foam.solid_fraction() < 0.8
    True
    """
    field = Field.empty(bounds, resolution)
    rng = np.random.default_rng(seed)

    # c runs from -1 (void) to +1 (solid); its mean sets the volume fraction.
    c = (2.0 * float(fraction) - 1.0) + 0.05 * rng.standard_normal(field.shape)
    epsilon = (feature / field.voxel) / 4.0

    frequencies = [2 * np.pi * np.fft.fftfreq(n) for n in field.shape]
    k2 = sum(np.meshgrid(*[f**2 for f in frequencies], indexing="ij"))
    denominator = 1.0 + dt * mobility * epsilon**2 * k2**2

    for _ in range(int(steps)):
        chemical = c**3 - c
        c = np.real(np.fft.ifftn((np.fft.fftn(c) - dt * mobility * k2 * np.fft.fftn(chemical)) / denominator))

    # Take the contour that holds the requested share of the volume, rather
    # than the nominal zero, then make the field metric.
    level = float(np.quantile(c, 1.0 - float(fraction)))
    foam = field.copy(level - c).redistanced()
    return foam.record(
        "spinodal", feature=feature, fraction=fraction, steps=int(steps), mobility=mobility, dt=dt, seed=seed
    )


def reaction_diffusion(bounds, resolution=96, feed=0.037, kill=0.06, du=0.16, dv=0.08, steps=1500, level=0.25, seed=2):
    """Gray-Scott reaction-diffusion, thresholded into a solid.

    Two chemicals, one feeding on the other, diffusing at different rates:
    the classic account of how a uniform medium patterns itself. In three
    dimensions the same equations give spots, worms and labyrinths depending
    on ``feed`` and ``kill``.

    **The least predictable process here, and included on those terms.** The
    parameter map is notoriously sensitive: neighbouring values give patterns
    that look nothing alike, and much of the map gives nothing at all -- the
    reaction dies out and leaves an empty field, or saturates and leaves a
    solid block. The defaults produce a connected blobby structure at the
    sizes tested here; for labyrinths, sweep ``feed`` in 0.02 to 0.04 and
    ``kill`` in 0.05 to 0.065 and look at what comes out. If you want an
    irregular porous solid with predictable dimensions, :func:`spinodal` is
    the better tool; this one is for when its particular character is what you
    are after.

    Parameters
    ----------
    bounds : :class:`compas.geometry.Box` | float | sequence
    resolution : int | tuple[int, int, int]
        The pattern scales with the *grid*, not with the domain: the same
        settings at twice the resolution give twice as many, half-size
        features.
    feed, kill : float
        The reaction. See above.
    du, dv : float
        Diffusion rates. ``du > dv`` is what makes patterns possible at all.
    steps : int
    level : float
        Concentration contour taken as the surface.
    seed : int

    Returns
    -------
    :class:`compas_vol.processes.Field`

    Raises
    ------
    ValueError
        If the reaction leaves no surface at ``level`` -- it died out or
        saturated. Change ``feed``/``kill``, or the level.
    """
    field = Field.empty(bounds, resolution)
    rng = np.random.default_rng(seed)

    u = np.ones(field.shape)
    v = np.zeros(field.shape)
    n = max(field.shape[0] // 8, 2)
    core = tuple(slice(s // 2 - n, s // 2 + n) for s in field.shape)
    u[core], v[core] = 0.5, 0.25
    u += 0.02 * rng.standard_normal(field.shape)
    v += 0.02 * rng.standard_normal(field.shape)

    def laplacian(a):
        return (
            np.roll(a, 1, 0) + np.roll(a, -1, 0)
            + np.roll(a, 1, 1) + np.roll(a, -1, 1)
            + np.roll(a, 1, 2) + np.roll(a, -1, 2)
            - 6 * a
        )

    for _ in range(int(steps)):
        reaction = u * v * v
        u = u + du * laplacian(u) - reaction + feed * (1 - u)
        v = v + dv * laplacian(v) + reaction - (feed + kill) * v

    pattern = field.copy(level - v)
    if not (pattern.values.min() < 0 < pattern.values.max()):
        raise ValueError(
            "The reaction left no surface at level={}: v runs {:.3f} to {:.3f}. "
            "It died out or saturated; change feed/kill or the level.".format(level, v.min(), v.max())
        )
    solid = pattern.redistanced()
    return solid.record(
        "reaction_diffusion", feed=feed, kill=kill, du=du, dv=dv, steps=int(steps), level=level, seed=seed
    )
