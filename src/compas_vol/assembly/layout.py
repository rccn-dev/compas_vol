"""Where to cut: away from what the design put there."""

import math

import numpy as np

__all__ = ["section_cost", "place_cuts"]


def section_cost(obj, axis, position, rect, step):
    """How much of a cut plane would miss material: the area of the section's voids.

    A joint bears on the material the cut passes through, so the more of the
    plane is solid, the better the joint. Cutting through an opening or a
    planter, or along a channel, loses a lot of that area; cutting across a
    channel loses a sliver. On a roof that falls to drains, a cut along a
    high line of the deck also loses less than one along a valley -- which
    keeps the joint out of the water as well. So the lower, the better the
    cut. A plane with no material at all costs infinity.

    Measure it on the drawn design rather than on everything: a foam or a
    texture is everywhere, says nothing about where a joint should go, and
    its noise drowns out the features that do.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The model.
    axis : int
        The axis the cut plane is perpendicular to.
    position : float
        Where along that axis.
    rect : sequence[float]
        The part of the plane to measure, ``(lo_a, lo_b, hi_a, hi_b)`` over
        the other two axes in order.
    step : float
        Sample spacing on the plane.

    Returns
    -------
    float

    Examples
    --------
    A slab with a hole: cutting through the hole misses the hole's section,
    cutting beside it misses nothing.

    >>> from compas.geometry import Box, Cylinder, Frame
    >>> from compas_vol.combinations import Subtraction
    >>> from compas_vol.primitives import VolBox, VolCylinder
    >>> slab = Subtraction(VolBox(Box(400, 200, 40), 0.0), VolCylinder(Cylinder(40, 100, frame=Frame.worldXY())))
    >>> section_cost(slab, 0, 0.0, (-100, -20, 100, 20), 2.0) > section_cost(slab, 0, 120.0, (-100, -20, 100, 20), 2.0)
    True
    """
    others = [a for a in range(3) if a != axis]
    na = max(2, int(math.ceil((rect[2] - rect[0]) / step)) + 1)
    nb = max(2, int(math.ceil((rect[3] - rect[1]) / step)) + 1)
    coordinates = [None, None, None]
    coordinates[axis] = np.full((1, 1, 1), float(position))
    shape_a = [1, 1, 1]
    shape_a[others[0]] = na
    shape_b = [1, 1, 1]
    shape_b[others[1]] = nb
    coordinates[others[0]] = np.linspace(rect[0], rect[2], na).reshape(shape_a)
    coordinates[others[1]] = np.linspace(rect[1], rect[3], nb).reshape(shape_b)
    values = np.asarray(obj.get_distance_numpy(*coordinates), dtype=float)
    solid = np.broadcast_to(values, np.broadcast_shapes(*[c.shape for c in coordinates])).squeeze(axis) < 0
    da = (rect[2] - rect[0]) / (na - 1)
    db = (rect[3] - rect[1]) / (nb - 1)
    if not solid.any():
        return math.inf
    return float((~solid).sum() * da * db)


def place_cuts(low, high, size, cost=None, shift=0.0, step=None):
    """Cut positions along one span, no piece longer than ``size``, each where it is cheapest.

    Starts from the even split -- the fewest pieces that fit -- and lets each
    cut move by up to ``shift`` to where ``cost`` is lowest, without any piece
    growing beyond ``size``. The choice is made for all cuts together, by
    dynamic programming over the candidate positions, so moving one cut
    never forces its neighbour into a worse place than it needed to be.

    Parameters
    ----------
    low, high : float
        The span to divide.
    size : float
        The largest piece allowed.
    cost : callable, optional
        ``cost(position) -> float``; lower is better. Without it the split
        stays even.
    shift : float
        How far a cut may move from the even split.
    step : float, optional
        Spacing of the candidate positions. Defaults to a twentieth of
        ``shift``.

    Returns
    -------
    list[float]
        The internal cut positions, in order. Empty if one piece fits.

    Examples
    --------
    A 5 m span in pieces of at most 3 m, with a feature at 2.4 m that the cut
    should avoid:

    >>> place_cuts(0.0, 5000.0, 3000.0)
    [2500.0]
    >>> place_cuts(0.0, 5000.0, 3000.0, cost=lambda x: -abs(x - 2400.0), shift=400.0)
    [2900.0]
    """
    count = max(1, int(math.ceil((high - low) / float(size) - 1e-9)))
    even = [low + (high - low) * n / count for n in range(1, count)]
    if not even or cost is None or shift <= 0:
        return [float(v) for v in even]

    step = float(step) if step else shift / 20.0
    offsets = np.arange(-shift, shift + 0.5 * step, step)
    candidates = [[c + o for o in offsets if low < c + o < high] for c in even]
    costs = [[float(cost(position)) for position in row] for row in candidates]

    # best[k][m]: least total cost with cut k at candidates[k][m].
    best = [costs[0][:]]
    back = [[None] * len(candidates[0])]
    for k in range(len(candidates)):
        if k == 0:
            # The first piece, from `low` to the first cut, must fit too.
            best[0] = [c if p - low <= size + 1e-9 else math.inf for p, c in zip(candidates[0], costs[0])]
            continue
        row, links = [], []
        for position, own in zip(candidates[k], costs[k]):
            options = [
                (best[k - 1][m] + own, m)
                for m, previous in enumerate(candidates[k - 1])
                if 0 < position - previous <= size + 1e-9
            ]
            total, link = min(options) if options else (math.inf, None)
            row.append(total)
            links.append(link)
        best.append(row)
        back.append(links)

    # The last piece, from the last cut to `high`, must fit as well.
    final = [b if high - p <= size + 1e-9 else math.inf for p, b in zip(candidates[-1], best[-1])]
    m = int(np.argmin(final))
    if not math.isfinite(final[m]):
        return [float(v) for v in even]
    chosen = []
    for k in range(len(candidates) - 1, -1, -1):
        chosen.append(candidates[k][m])
        m = back[k][m]
    return [float(v) for v in reversed(chosen)]
