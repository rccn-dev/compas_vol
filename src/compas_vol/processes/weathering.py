"""Processes that take material away.

Each is a speed term handed to :func:`compas_vol.processes.evolve`, or a
single displacement where nothing needs iterating. They are presets, not the
API: the terms they are built from compose into any other rule you want.

None of these is a physical simulation. There is no mass conservation, no
transported sediment, no time in seconds -- what they reproduce is the
*shape* a mechanism leaves behind, with parameters in millimetres so the
result can be dimensioned rather than tuned by eye.
"""

import numpy as np

from compas_vol.runtime import require

from .evolve import evolve
from .evolve import steps_for
from .noise import fbm
from .terms import Concavity
from .terms import Convexity
from .terms import Uniform
from .terms import Values

__all__ = ["hardness", "abrasion", "differential", "pitting", "strata", "runoff", "jointing"]


def hardness(field, cell_size=25.0, octaves=5, seed=0):
    """A noise field standing in for how resistant the rock is, in ``[-1, 1]``.

    Defined on world coordinates, so the same design weathers the same way at
    any resolution.

    Returns
    -------
    :class:`numpy.ndarray`
    """
    return fbm(*field.coordinates(), cell_size=cell_size, octaves=octaves, seed=seed)


def abrasion(field, depth=4.0, steps=12, length=9.0, edge_bias=2.0):
    """Rounding: what sticks out wears first.

    Convex parts of the surface meet the wind, the water and the passer-by;
    hollows are sheltered. Running this far enough turns any massing into a
    boulder, which is also its limit -- it only ever removes distinction.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
    depth : float
        Millimetres removed from a flat face. An edge loses up to
        ``(1 + edge_bias)`` times that, which is what rounds it. Read it as a
        nominal depth: as the model rounds, what was a flat face becomes
        slightly convex and so wears somewhat faster than the number says --
        about 1.5x with the default bias. With ``edge_bias=0`` it is exact.
    steps : int
        Raised automatically if that many steps could not cover ``depth``
        without outrunning the grid; the history records what was used.
    length : float
        Feature size curvature is measured against, in mm. Roughly the radius
        the sharpest edge ends up with.
    edge_bias : float
        How much faster a fully convex point wears than a flat one. 0 wears
        everything equally.

    Returns
    -------
    :class:`compas_vol.processes.Field`
    """
    steps = steps_for(depth, steps, field, peak=1.0 + edge_bias)
    rate = depth / steps
    speed = Uniform(rate) * (1.0 + edge_bias * Convexity(length=length))
    return evolve(field, speed, steps=steps).record(
        "abrasion", depth=depth, steps=steps, length=length, edge_bias=edge_bias
    )


def differential(field, resistance=None, depth=7.0, cell_size=25.0, octaves=5, seed=0):
    """Soft rock retreats, hard rock stands proud. One pass, no iteration.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
    resistance : array-like, optional
        Values in ``[-1, 1]``; 1 resists completely. Defaults to
        :func:`hardness` noise.
    depth : float
        Millimetres removed where the rock is softest.
    cell_size, octaves, seed
        Passed to :func:`hardness` when ``resistance`` is not given.

    Returns
    -------
    :class:`compas_vol.processes.Field`
    """
    if resistance is None:
        resistance = hardness(field, cell_size=cell_size, octaves=octaves, seed=seed)
    else:
        resistance = np.asarray(resistance, dtype=float)
    return field.displaced(depth * (0.5 - 0.5 * resistance)).record(
        "differential", depth=depth, cell_size=cell_size, octaves=octaves, seed=seed
    )


def pitting(field, resistance=None, depth=9.0, steps=12, length=6.0, threshold=0.2, feedback=1.7,
            cell_size=25.0, octaves=5, seed=0):
    """Hollows deepen faster than the faces around them: tafoni, honeycombing.

    Two ingredients. Pits start where the rock is weakest, and then run away
    with it, because a hollow shelters itself -- the concavity term feeds its
    own growth. Left long enough, neighbouring pits merge into the honeycombed
    walls you see in sandstone, and into the pockmarked skin MVRDV describes
    for Rotterdam ROCKS.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
    resistance : array-like, optional
        How resistant the rock is, in ``[-1, 1]``, in the same sense as
        :func:`differential`: ``1`` never pits. Defaults to :func:`hardness`
        noise. Set it to ``1`` wherever pitting must not happen -- a surface
        that carries water, a face that has to stay flat.
    depth : float
        Millimetres removed where the rock is weakest and the hollow is
        deepest. Everywhere else loses less, most of it nothing at all --
        which is the difference between pitting and general weathering.
    steps : int
        Raised automatically if that many steps could not cover ``depth``;
        the history records what was used.
    length : float
        Curvature length, in mm: roughly the width of the pits.
    threshold : float
        How far below average the resistance must fall for the rock to pit:
        it pits where ``resistance < -threshold``. Raise it for fewer, more
        separated hollows.
    feedback : float
        How much a hollow accelerates its own deepening. Near zero this is
        just :func:`differential`; high values cut through.
    cell_size, octaves, seed
        Passed to :func:`hardness` when ``resistance`` is not given.

    Returns
    -------
    :class:`compas_vol.processes.Field`
    """
    if resistance is None:
        resistance = hardness(field, cell_size=cell_size, octaves=octaves, seed=seed)
    else:
        resistance = np.asarray(resistance, dtype=float)
    weak = np.clip((-resistance - threshold) / (1.0 - threshold), 0.0, 1.0)
    # Normalised by its own maximum, so `depth` is millimetres at the weakest,
    # most concave point rather than an arbitrary scale factor.
    seeding = 0.3
    steps = steps_for(depth, steps, field)
    rate = depth / steps / (seeding + feedback)
    speed = Uniform(rate) * Values(weak) * (seeding + feedback * Concavity(length=length))
    return evolve(field, speed, steps=steps).record(
        "pitting", depth=depth, steps=steps, length=length, threshold=threshold, feedback=feedback,
        cell_size=cell_size, octaves=octaves, seed=seed
    )


def strata(field, thickness=10.0, dip=(0.2, 0.08), depth=5.0, wobble=3.0, contrast=2.5, seed=1):
    """Bedding: alternating hard and soft layers, weathering unevenly.

    The layers are planes, tilted by ``dip`` and bent by noise, so what comes
    out are ledges and overhangs that follow the bedding through the mass --
    not a pattern applied to the surface. This is the cheapest way to make a
    massing read as rock rather than as a blob.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
    thickness : float
        Bed thickness, in mm.
    dip : tuple[float, float]
        Slope of the beds along X and Y.
    depth : float
        Millimetres removed from the softest beds.
    wobble : float
        How far the beds wander, in mm.
    contrast : float
        Sharpness of the change between hard and soft.
    seed : int

    Returns
    -------
    :class:`compas_vol.processes.Field`
    """
    x, y, z = field.coordinates()
    level = z + dip[0] * x + dip[1] * y
    if wobble:
        level = level + wobble * fbm(x, y, z, cell_size=6 * thickness, octaves=3, seed=seed)
    beds = np.clip(contrast * np.sin(2 * np.pi * level / thickness), -1.0, 1.0)
    return field.displaced(depth * (0.5 - 0.5 * beds)).record(
        "strata", thickness=thickness, dip=tuple(dip), depth=depth, wobble=wobble, contrast=contrast, seed=seed
    )


def runoff(field, depth=6.0, decay=10.0, smooth=0.9, concentration=0.4):
    """Rain: water gathers downhill and cuts where it concentrates.

    Flow accumulation over the upper surface -- the topmost solid voxel of
    each column -- so it describes the parts a raindrop can actually reach.
    Undersides and the inside of overhangs are left alone, which is true of
    rain and is also this method's limit: it knows nothing about the sides.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
    depth : float
        Millimetres cut where flow is heaviest.
    decay : float
        How far the cut reaches below the surface, in mm.
    smooth : float
        Blur on the flow map, in voxels. Higher gives fewer, broader channels.
    concentration : float
        Exponent on accumulated flow. Lower spreads the cutting out; higher
        concentrates it into a few deep gullies.

    Returns
    -------
    :class:`compas_vol.processes.Field`
    """
    ndimage = require("scipy.ndimage")

    inside = field.values < 0
    if not inside.any():
        raise ValueError("Nothing to erode: the field has no solid in it.")

    nz = field.shape[2]
    top = np.where(inside.any(axis=2), nz - 1 - np.argmax(inside[:, :, ::-1], axis=2), -1)
    height = np.where(top >= 0, field.origin[2] + top * field.spacing[2], -np.inf)

    water = np.where(top >= 0, 1.0, 0.0)
    carried = np.zeros_like(water)
    rows, columns = np.unravel_index(np.argsort(height, axis=None)[::-1], height.shape)
    offsets = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    ni, nj = height.shape

    for i, j in zip(rows, columns):
        if not np.isfinite(height[i, j]):
            continue
        drop, target = 0.0, None
        for di, dj in offsets:
            a, b = i + di, j + dj
            if 0 <= a < ni and 0 <= b < nj and np.isfinite(height[a, b]):
                fall = height[i, j] - height[a, b]
                if fall > drop:
                    drop, target = fall, (a, b)
        if target is None:
            continue
        # A steeper slope carries more, so it cuts more.
        carried[i, j] += water[i, j] * min(1.0, drop / field.spacing[2])
        water[target] += water[i, j]

    cut = ndimage.gaussian_filter(np.power(carried, concentration), smooth)
    cut = depth * cut / max(cut.max(), 1e-9)
    zs = field.origin[2] + np.arange(nz) * field.spacing[2]
    below = np.clip(height[:, :, None] - zs[None, None, :], 0, None)
    return field.displaced(cut[:, :, None] * np.exp(-below / decay)).record(
        "runoff", depth=depth, decay=decay, smooth=smooth, concentration=concentration
    )


def jointing(field, count=25, opening=2.5, reach=12.0, seed=4, points=None):
    """Joints: the mass breaks into blocks before it wears.

    Rock is jointed long before it is rounded, and weathering opens the joints
    first, which is why outcrops read as stacked blocks rather than as one
    lump. The joint set is a Voronoi diagram: cell walls become open seams.

    Seams taper with depth, closing ``reach`` millimetres in. Weathering works
    from the outside, so that is what a jointed outcrop looks like -- but it
    is also what keeps the result a single object. A seam carried all the way
    through separates the blocks completely, and a model that has quietly
    become twenty loose stones cannot be built or printed. Set ``reach``
    larger than the mass to cut it through deliberately.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
    count : int
        Number of blocks, if ``points`` is not given.
    opening : float
        Seam width at the surface, in mm.
    reach : float
        How far in the seams stay open, in mm.
    seed : int
    points : sequence[point], optional
        Block centres, to place the joints deliberately.

    Returns
    -------
    :class:`compas_vol.processes.Field`
    """
    from compas_vol.microstructures import Voronoi

    x0, y0, z0, x1, y1, z1 = field.bounds
    if points is None:
        rng = np.random.default_rng(seed)
        points = rng.uniform((x0, y0, z0), (x1, y1, z1), (int(count), 3)).tolist()

    joints = Voronoi([tuple(map(float, p)) for p in points], opening)
    seams = np.asarray(joints.get_distance_numpy(*field.coordinates()))

    # Taper: full width at the surface, closed `reach` millimetres inside.
    taper = np.exp(np.minimum(field.values, 0.0) / max(reach, 1e-9))
    tapered = seams + 0.5 * opening * (1.0 - taper)

    opened = field.copy(np.maximum(field.values, -tapered)).redistanced()
    return opened.record("jointing", count=len(points), opening=opening, reach=reach, seed=seed)
