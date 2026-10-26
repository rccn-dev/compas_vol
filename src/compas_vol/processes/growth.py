"""Processes that add material.

Growth is :func:`compas_vol.processes.evolve` with a negative speed, and that
is the whole difference from weathering -- until the growth is *unstable*,
which is where the interesting shapes come from and where the care is needed.

A surface that grows faster where it already bulges amplifies every bump it
has, including the ones a single voxel wide. Left alone that produces noise at
the resolution of the grid, which is not a design. Two things keep it honest:
curvature measured against a real length, and a smoothed speed, which together
pick the wavelength the result actually takes.
"""

import math

import numpy as np

from compas_vol.runtime import require

from .evolve import evolve
from .evolve import steps_for
from .field import Field
from .terms import Curvature
from .terms import Shelter
from .terms import Smooth
from .terms import Uniform

__all__ = ["fingering", "accretion", "diffusion_limited", "branching"]


def fingering(field, height=30.0, length=9.0, gain=1.4, wavelength=4.0, limit=0.5, steps=None):
    """Growth that folds: the surface buckles into lobes and valleys.

    Speed rises with curvature, so a bulge outgrows the surface beside it and
    becomes a lobe, while the valley between two lobes is left behind. That is
    the brain-coral mechanism, and in a field it needs no mesh, no vertex
    insertion and no collision handling -- lobes that meet simply merge.

    An unstable process runs at the fastest rate the grid allows: the speed is
    a *shape*, and :func:`compas_vol.processes.evolve` scales it to half a
    voxel per step. The step count therefore has to follow the resolution,
    and it is derived here rather than asked for -- ``height`` is in
    millimetres, and the same design grows the same distance at any
    resolution. Given as a step count instead, a model grown at 0.6 mm voxels
    comes out two thirds the size of the same model at 1.0 mm, which is a
    silent way to lose a design.

    A finer grid then takes more steps to cover the same distance, and more
    steps mean more time for the instability to work: the same height comes
    out with finer, more numerous folds. That is resolution buying detail,
    which is the behaviour you want.

    Two parameters decide whether this works at all, and both are lengths:

    * ``length`` -- what curvature is measured against. Curvature has units of
      1/length; compared against the voxel size instead of a real dimension
      the term vanishes and the model inflates into a sphere. The failure is
      silent, which is what makes it worth naming.
    * ``wavelength`` -- how far the speed is smoothed, which sets the width of
      a fold. Without it the instability amplifies the one-voxel wavelength
      as eagerly as any other, and the result is noise at grid resolution.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
        Starting solid. Give it room: the surface grows outward, and anything
        reaching the edge of the grid is cut off there.
    height : float
        Millimetres the fastest part of the surface advances.
    length : float
        Length curvature is measured against, in mm.
    gain : float
        Strength of the instability. At 0 this is uniform growth; past about
        1.5 lobes pinch off and leave loose pieces behind.
    wavelength : float
        Smoothing length on the speed, in mm: roughly the width of a fold.
    limit : float
        Advance per step, as a fraction of a voxel.
    steps : int, optional
        Override the derived step count. Then ``height`` is ignored and the
        advance goes back to depending on the grid.

    Returns
    -------
    :class:`compas_vol.processes.Field`
    """
    if steps is None:
        steps = max(1, math.ceil(height / (limit * field.voxel)))
    speed = Smooth(Uniform(-1.0) * (1.0 + gain * Curvature(length=length)), length=wavelength)
    return evolve(field, speed, steps=steps, limit=limit).record(
        "fingering", height=height, steps=steps, length=length, gain=gain, wavelength=wavelength, limit=limit
    )


def accretion(field, height=4.0, steps=10, reach=8.0, shelter=1.6):
    """Growth that fills hollows: material settles where it is sheltered.

    The opposite bias to :func:`compas_vol.processes.pitting`, and the same
    machinery. Deposition -- travertine, flowstone, silting -- lands where
    flow is slow, which is in the hollows, so the surface smooths and fills
    rather than pitting. Useful for softening a model that erosion has left
    too jagged to build.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
    height : float
        Millimetres deposited in the most sheltered places. Exposed faces get
        little, which is how the surface smooths.
    steps : int
        Raised automatically if that many steps could not cover ``height``.
    reach : float
        How far around each point shelter is measured, in mm.
    shelter : float
        How strongly deposition prefers hollows. At 0 it coats everything.

    Returns
    -------
    :class:`compas_vol.processes.Field`
    """
    exposed = 0.2
    steps = steps_for(height, steps, field)
    rate = height / steps / (exposed + shelter)
    speed = Uniform(-rate) * (exposed + shelter * Shelter(reach=reach))
    return evolve(field, speed, steps=steps).record(
        "accretion", height=height, steps=steps, reach=reach, shelter=shelter
    )


def diffusion_limited(field, height=8.0, steps=30, supply_iterations=200, coarsen=2, tension=0.25, length=9.0):
    """Growth fed by a diffusing supply: the mechanism behind dendrites.

    A nutrient field is harmonic in the empty space, zero at the surface and
    one at the edge of the domain; the surface advances in proportion to the
    gradient that reaches it. A tip reaches further into the supply than the
    surface beside it, so it grows faster -- the Mullins-Sekerka instability,
    and the closest thing here to a first-principles account of branching.

    **This one is demanding, and honest results need patience.** In testing at
    100 mm across, 30 steps and a domain wall 50 mm away, the surface stayed
    smooth: the supply barely varies over a small, nearly convex body, and a
    nearby boundary screens what variation there is. It wants a domain several
    times the size of the seed and hundreds of steps before fingers appear.
    For branching at a useful cost, :func:`fingering` and :func:`branching`
    get there sooner; this is here because it is the mechanism the others
    imitate.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
    height : float
        Millimetres of advance overall.
    steps : int
    supply_iterations : int
        Jacobi sweeps per step for the nutrient field. Too few leaves the
        supply undiffused and the growth uniform.
    coarsen : int
        Solve the supply on a grid this many times coarser. The field is
        smooth, so it upsamples cleanly and costs a fraction.
    tension : float
        Curvature damping, which sets the finest branch that survives.
    length : float
        Length curvature is measured against, in mm.

    Returns
    -------
    :class:`compas_vol.processes.Field`
    """
    ndimage = require("scipy.ndimage")

    rate = height / max(int(steps), 1)

    def speed(current):
        small = current.values[::coarsen, ::coarsen, ::coarsen]
        solid = small < 0
        supply = np.ones_like(small)
        supply[solid] = 0.0
        for _ in range(int(supply_iterations)):
            supply = (
                np.roll(supply, 1, 0) + np.roll(supply, -1, 0)
                + np.roll(supply, 1, 1) + np.roll(supply, -1, 1)
                + np.roll(supply, 1, 2) + np.roll(supply, -1, 2)
            ) / 6.0
            supply[solid] = 0.0
            supply[0], supply[-1] = 1.0, 1.0
            supply[:, 0], supply[:, -1] = 1.0, 1.0
            supply[:, :, 0], supply[:, :, -1] = 1.0, 1.0
        zoom = [s / c for s, c in zip(current.shape, supply.shape)]
        supply = ndimage.zoom(supply, zoom, order=1)[: current.shape[0], : current.shape[1], : current.shape[2]]
        flux = np.sqrt(sum(g * g for g in np.gradient(supply, *current.spacing)))
        near = np.abs(current.values) < 2 * current.voxel
        scale = np.percentile(flux[near], 90) if near.any() else 1.0
        advance = np.clip(flux / max(scale, 1e-9), 0.0, 3.0)
        return -rate * advance + tension * rate * Curvature(length=length)(current)

    return evolve(field, speed, steps=steps).record(
        "diffusion_limited", height=height, steps=steps, supply_iterations=supply_iterations, tension=tension
    )


def branching(bounds, resolution=128, attractors=800, root=(0, 0, None), step=3.5, influence=22.0, kill=5.0,
              radius=(1.5, 5.0), iterations=200, exponent=2.6, seed=3):
    """Branching built as a graph, then drawn into the field.

    Space colonization (Runions et al., 2007): tips grow towards the attractor
    points that claim them, attractors are removed once reached, and a tip
    pulled two ways splits. Branch thickness follows how many tips a branch
    feeds, so the structure tapers the way a tree or a vascular network does.

    This is the one process here that does not evolve a level set. Growth by
    competition is a question about topology -- who connects to what -- and a
    graph answers it directly, where a field would have to discover it. The
    result is rasterised into a distance field as tapered capsules, so from
    the outside it behaves like every other process.

    Parameters
    ----------
    bounds : :class:`compas.geometry.Box` | float | sequence
        The domain to grow into and sample.
    resolution : int | tuple[int, int, int]
    attractors : int
        Points competing to be reached. More gives a denser network.
    root : tuple[float, float, float]
        Where growth starts. ``None`` in a slot means the low end of the
        domain on that axis.
    step : float
        Length of one growth step, in mm.
    influence : float
        How far a tip can be claimed from, in mm.
    kill : float
        How close a tip must come for an attractor to be consumed, in mm.
    radius : tuple[float, float]
        Thinnest and thickest branch radius, in mm.
    iterations : int
    exponent : float
        Murray-like exponent relating branch radius to the tips it feeds.
    seed : int

    Returns
    -------
    :class:`compas_vol.processes.Field`
    """
    field = Field.empty(bounds, resolution)
    x0, y0, z0, x1, y1, z1 = field.bounds
    rng = np.random.default_rng(seed)

    centre = np.array([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    extent = np.array([x1 - x0, y1 - y0, z1 - z0]) / 2
    cloud = rng.uniform(-1, 1, (int(attractors) * 3, 3))
    cloud = cloud[np.linalg.norm(cloud, axis=1) <= 1][: int(attractors)] * extent * 0.9 + centre

    start = [c if c is not None else lo for c, lo in zip(root, (x0, y0, z0))]
    nodes = [np.array(start, dtype=float)]
    parents = [-1]

    for _ in range(int(iterations)):
        if not len(cloud):
            break
        positions = np.array(nodes)
        distances = np.linalg.norm(cloud[:, None, :] - positions[None, :, :], axis=2)
        nearest = distances.argmin(axis=1)
        claimed = distances[np.arange(len(cloud)), nearest] < influence
        pulls = {}
        for point, node, ok in zip(cloud, nearest, claimed):
            if ok:
                pulls.setdefault(int(node), []).append(point)
        if not pulls:
            break
        for node, claims in pulls.items():
            direction = np.mean([c - nodes[node] for c in claims], axis=0)
            length = np.linalg.norm(direction)
            if length < 1e-9:
                continue
            nodes.append(nodes[node] + step * direction / length)
            parents.append(node)
        positions = np.array(nodes)
        alive = np.linalg.norm(cloud[:, None, :] - positions[None, :, :], axis=2).min(axis=1) > kill
        cloud = cloud[alive]

    if len(nodes) < 2:
        raise ValueError("Nothing grew: no attractor was within `influence` of the root.")

    fed = np.ones(len(nodes))
    for index in range(len(nodes) - 1, 0, -1):
        fed[parents[index]] += fed[index]
    thickness = radius[0] + (radius[1] - radius[0]) * (fed / fed.max()) ** (1.0 / exponent)

    x, y, z = field.coordinates()
    values = np.full(field.shape, float(max(x1 - x0, y1 - y0, z1 - z0)))
    for index in range(1, len(nodes)):
        a, b = np.array(nodes[parents[index]]), np.array(nodes[index])
        segment = b - a
        along = (x - a[0]) * segment[0] + (y - a[1]) * segment[1] + (z - a[2]) * segment[2]
        t = np.clip(along / max(segment @ segment, 1e-9), 0.0, 1.0)
        distance = np.sqrt(
            (x - a[0] - t * segment[0]) ** 2
            + (y - a[1] - t * segment[1]) ** 2
            + (z - a[2] - t * segment[2]) ** 2
        )
        r = thickness[parents[index]] + t * (thickness[index] - thickness[parents[index]])
        np.minimum(values, distance - r, out=values)

    grown = field.copy(values).redistanced()
    return grown.record("branching", attractors=int(attractors), nodes=len(nodes), step=step, seed=seed)
