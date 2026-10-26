"""The one operator every process is built from."""

import math

import numpy as np

from .terms import evaluate
from .terms import gradient_magnitude_of

__all__ = ["evolve", "steps_for"]


def steps_for(depth, steps, field, peak=1.0, limit=0.5):
    """Enough steps that the cap never binds, so ``depth`` is honoured.

    A preset asks for millimetres, and :func:`evolve` refuses to move the
    surface more than ``limit`` voxels per step. If the fastest point of the
    speed field would exceed that, the step is scaled down and the surface
    ends up short of the depth asked for -- silently, which is the problem.
    Raising the step count instead keeps the promise and costs proportionally
    more time.

    Parameters
    ----------
    depth : float
        Millimetres the surface should travel where it is fastest.
    steps : int
        Steps the caller asked for; the return value is never fewer.
    field : :class:`compas_vol.processes.Field`
    peak : float
        The largest multiplier the speed term can reach.
    limit : float
        Cap per step, as a fraction of a voxel.

    Returns
    -------
    int
    """
    needed = math.ceil(abs(peak * depth) / max(limit * field.voxel, 1e-12))
    return max(int(steps), int(needed))


def evolve(field, speed, steps=10, redistance_every=1, limit=0.5):
    """Move the surface along its normal, repeatedly.

    One loop covers erosion and growth alike::

        phi <- phi + speed * |grad phi|      then redistance

    A **positive** speed drives the surface into the solid: wearing, pitting,
    dissolving. A **negative** speed pushes it outward: growing, depositing,
    accreting. Nothing else distinguishes the two, which is why they share an
    operator, and why the interesting part of a process is its speed term
    rather than its loop.

    No step may move the surface further than a fraction of a voxel: a level
    set advanced further than that outruns the grid it is sampled on. When a
    speed would exceed it, **the whole speed field is scaled down rather than
    clipped point by point**. That distinction matters more than it looks. An
    unstable process -- growth that runs faster where the surface bulges --
    lives on the *differences* between one part of the surface and another,
    and clipping flattens every fast point to the same value, which quietly
    turns folding growth into uniform growth. Scaling keeps the ratios and
    only slows the clock.

    If the cap binds, the surface travels less far than ``speed * steps``
    asks. The history records how many steps were limited; raise ``steps``
    (smaller step each) or lower the depth if it is most of them.

    Parameters
    ----------
    field : :class:`compas_vol.processes.Field`
        The starting field. Not modified.
    speed : :class:`compas_vol.processes.terms.Term` | callable | float | array
        Millimetres of advance per step, per point.
    steps : int
        How many steps. Together with the speed, this sets how far the surface
        travels; a preset usually splits a total depth across the steps.
    redistance_every : int
        Rebuild the distance field every n steps. Every step is safest;
        more than about three lets the field drift far enough from metric that
        the speed terms start measuring the wrong thing.
    limit : float
        Cap per step, as a fraction of a voxel.

    Returns
    -------
    :class:`compas_vol.processes.Field`
        A new field, redistanced, with the operation recorded in its history.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.processes import Field, evolve
    >>> from compas_vol.processes.terms import Uniform
    >>> field = Field.from_object(VolSphere(Sphere(20, point=Point(0, 0, 0))), bounds=30.0, resolution=40)
    >>> worn = evolve(field, Uniform(0.25), steps=8)          # 2 mm off every face
    >>> before = field.to_volume().get_distance([25, 0, 0])   # 5 mm outside the sphere
    >>> after = evolve(field, Uniform(0.25), steps=8).to_volume().get_distance([25, 0, 0])
    >>> round(after - before, 1)                              # the surface retreated 2 mm
    2.0
    """
    working = field.copy(field.values.copy())
    cap = limit * field.voxel
    limited = 0

    for step in range(int(steps)):
        rate = working.falloff(evaluate(speed, working))
        fastest = float(np.abs(rate).max())
        if fastest > cap:
            rate = rate * (cap / fastest)
            limited += 1
        working = working.copy(working.values + rate * gradient_magnitude_of(working))
        if redistance_every and (step + 1) % int(redistance_every) == 0:
            working = working.redistanced()

    result = working.redistanced()
    return result.record(
        "evolve",
        speed=repr(speed),
        steps=int(steps),
        redistance_every=int(redistance_every),
        limit=float(limit),
        steps_limited=limited,
    )
