from compas.geometry import Point

from compas_vol.base import VolObject
from compas_vol.base import format_number


class Voronoi(VolObject):
    """The cell walls of a 3D Voronoi diagram over a set of seed points.

    A point lies on a wall when it is equidistant from its two nearest seeds,
    so the field is the distance to the nearest bisecting plane, thickened by
    ``thickness``.

    The COMPAS 1 implementation took ``min(d1, d2)`` where ``d1`` was the
    squared distance from the *world origin* to the nearest seed -- a quantity
    that does not depend on the query point at all -- so the result was not a
    Voronoi field. It also imported from ``numpy.core``, a private module
    removed in NumPy 2, which made the module fail to import outright.

    Parameters
    ----------
    points : sequence[point]
        The seed points of the diagram.
    thickness : float
        The thickness of the cell separation walls.
    walls : bool
        If ``True`` (the default) the solid is the wall network. If ``False``
        the solid is the cell interiors, separated by gaps of ``thickness``.

    Examples
    --------
    >>> from compas_vol.microstructures import Voronoi
    >>> seeds = [(0, 0, 0), (10, 0, 0), (0, 10, 0), (0, 0, 10)]
    >>> v = Voronoi(seeds, 1.0)
    >>> round(v.get_distance([5, 0, 0]), 6)
    -0.5
    """

    def __init__(self, points=None, thickness=1.0, walls=True, name=None):
        super().__init__(name=name)
        self._thickness = None
        self.points = [tuple(p) for p in points] if points else []
        self.thickness = thickness
        self.walls = walls

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "points": [list(p) for p in self.points],
            "thickness": self.thickness,
            "walls": self.walls,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(data["points"], data["thickness"], data["walls"])

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def thickness(self):
        """float: The thickness of the cell separation walls."""
        return self._thickness

    @thickness.setter
    def thickness(self, thickness):
        self._thickness = float(thickness)

    def __repr__(self):
        return "Voronoi({0} points,{1},{2})".format(
            len(self.points), format_number(self.thickness), self.walls
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)

        # The nearest seed defines the cell the point falls in.
        nearest = min(self.points, key=lambda c: p.distance_to_point(Point(*c)))

        # The wall distance is the smallest distance to any bisecting plane
        # between the nearest seed and one of the others.
        best = float("inf")
        for c in self.points:
            if c == nearest:
                continue
            ex, ey, ez = c[0] - nearest[0], c[1] - nearest[1], c[2] - nearest[2]
            length = (ex * ex + ey * ey + ez * ez) ** 0.5
            if length == 0:
                continue
            mx, my, mz = (nearest[0] + c[0]) / 2, (nearest[1] + c[1]) / 2, (nearest[2] + c[2]) / 2
            d = ((p.x - mx) * ex + (p.y - my) * ey + (p.z - mz) * ez) / length
            best = min(best, abs(d))

        if not self.walls:
            return self.thickness / 2 - best
        return best - self.thickness / 2

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        coords = np.asarray(self.points, dtype=float)
        shape = np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z))

        blockable = len(coords) >= _MIN_SEEDS_TO_BLOCK and len(shape) == 3 and min(shape) > 1
        if blockable:
            wall = _walls_blocked(coords, x, y, z, shape)
        else:
            wall, _ = _walls(coords, *_broadcast(x, y, z, shape))

        if not self.walls:
            return self.thickness / 2 - wall
        return wall - self.thickness / 2


#: Below this many seeds, walking all of them costs less than the bookkeeping
#: of splitting the grid into blocks.
_MIN_SEEDS_TO_BLOCK = 24

#: Voxels per axis in a block, for the serial and the threaded formulation.
#: Smaller blocks prune harder but repeat the per-block setup more often.
#: Measured over 50 to 800 seeds at 200^3.
_BLOCK = 16
_BLOCK_THREADED = 32

#: Candidate seeds handled at once by the threaded formulation. At 32^3 points
#: against 64 seeds each intermediate is a few MB: big enough that a worker
#: holds the GIL for milliseconds at a time rather than microseconds.
_CHUNK = 64


def _broadcast(x, y, z, shape):
    import numpy as np

    return (np.broadcast_to(c, shape) for c in (x, y, z))


def _walls(coords, px, py, pz):
    """Distance to the nearest Voronoi wall, walking every seed given.

    Returns the wall distance and, as a by-product, the largest distance from
    any point of the grid to its own nearest seed, which the blocked variant
    uses to tighten its bounds.

    Two passes over the seeds: the first finds which cell each point is in,
    the second the closest bisecting plane between that cell's seed and any
    other. Looping keeps peak memory at O(grid) instead of the
    O(grid * seeds) a fully broadcast formulation needs -- at 160^3 with 120
    seeds the broadcast version wants tens of gigabytes.
    """
    import numpy as np

    shape = px.shape

    best_d2 = np.full(shape, np.inf)
    nearest = np.zeros(shape, dtype=np.intp)
    for i, (cx, cy, cz) in enumerate(coords):
        d2 = (px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2
        closer = d2 < best_d2
        best_d2 = np.where(closer, d2, best_d2)
        nearest = np.where(closer, i, nearest)

    nx = coords[nearest, 0]
    ny = coords[nearest, 1]
    nz = coords[nearest, 2]

    wall = np.full(shape, np.inf)
    for cx, cy, cz in coords:
        ex, ey, ez = cx - nx, cy - ny, cz - nz
        length = np.sqrt(ex * ex + ey * ey + ez * ez)
        # length == 0 is a seed's bisector with itself, which is degenerate.
        valid = length > 0
        safe = np.where(valid, length, 1.0)
        mx, my, mz = (nx + cx) / 2, (ny + cy) / 2, (nz + cz) / 2
        d = np.abs(((px - mx) * ex + (py - my) * ey + (pz - mz) * ez) / safe)
        wall = np.where(valid, np.minimum(wall, d), wall)
    return wall, float(np.sqrt(best_d2).max())


def _walls_blocked(coords, x, y, z, shape):
    """The same field, but each block of the grid sees only the seeds it can.

    A Voronoi field is local: a seed on the far side of the model cannot
    affect this corner of the grid. Splitting the grid into blocks and
    discarding the seeds that provably cannot matter turns the cost from
    "every seed for every voxel" into "a handful of seeds for every voxel" --
    measured 5 to 25 times faster from 150 seeds up, and exact, not an
    approximation.

    Two bounds do the discarding, for a block ``B``:

    * The nearest seed of any point in ``B`` is at most ``R`` away, where
      ``R = min over seeds of (farthest distance from B to that seed)``. Any
      seed whose *nearest* distance to ``B`` exceeds ``R`` can be dropped
      from the search for the containing cell.
    * A bisecting plane between the containing seed ``n`` and a seed ``c``
      is at least ``(|pc| - |pn|) / 2`` from ``p``. So once the walls are
      known to be no further than ``W`` anywhere in the block, and no point
      is further than ``N`` from its own seed, seeds beyond ``N + 2W`` cannot
      own a closer wall. Both ``N`` and ``W`` are measured on the candidate
      set as it stands; adding seeds only lowers them, so the check is re-run
      against the widened radius until it holds.
    """
    import numpy as np

    wall = np.empty(shape, dtype=float)
    eps = 1e-9 * (1 + float(np.abs(coords).max()))
    walls, block_size = _formulation()

    for block in _blocks(shape, block_size):
        xb, yb, zb = (_slice(c, axis, block[axis]) for axis, c in enumerate((x, y, z)))
        sub = tuple(slice(*block[axis]) for axis in range(3))
        block_shape = tuple(hi - lo for lo, hi in block)
        px, py, pz = _broadcast(xb, yb, zb, block_shape)

        lo = np.array([float(np.min(c)) for c in (xb, yb, zb)])
        hi = np.array([float(np.max(c)) for c in (xb, yb, zb)])
        # Distance from the block's box to each seed, nearest and farthest.
        d_min = np.linalg.norm(np.maximum(np.maximum(lo - coords, coords - hi), 0.0), axis=1)
        d_max = np.linalg.norm(np.maximum(np.abs(coords - lo), np.abs(coords - hi)), axis=1)
        radius = float(d_max.min())

        points = np.stack(np.broadcast_arrays(px, py, pz), axis=-1).reshape(-1, 3)

        keep = d_min <= radius + eps
        for _ in range(4):
            block_wall, nearest_reach = walls(coords[keep], points)
            widest = float(np.max(block_wall))
            if not np.isfinite(widest):
                block_wall, _ = walls(coords, points)
                break
            needed = d_min <= nearest_reach + 2 * widest + eps
            if not (needed & ~keep).any():
                break
            keep = needed
        else:
            # Four widenings without settling: take every seed and be done.
            block_wall, _ = walls(coords, points)

        block_wall = block_wall.reshape(block_shape)
        wall[sub] = block_wall
    return wall


def _walls_flat(coords, points):
    """Wall distance for a flat list of points, looping over the seeds.

    The fastest formulation when it has a core to itself: each NumPy call
    touches one array per point, so the working set stays in cache.

    Parameters
    ----------
    coords : :class:`numpy.ndarray`
        Candidate seeds, shape ``(k, 3)``.
    points : :class:`numpy.ndarray`
        Query points, shape ``(m, 3)``.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, float]
        The wall distance per point, and the largest distance from a point to
        its own nearest seed.
    """
    import numpy as np

    px, py, pz = points[:, 0], points[:, 1], points[:, 2]
    best = np.full(len(points), np.inf)
    nearest = np.zeros(len(points), dtype=np.intp)
    for i, (cx, cy, cz) in enumerate(coords):
        d2 = (px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2
        closer = d2 < best
        best = np.where(closer, d2, best)
        nearest = np.where(closer, i, nearest)

    own = coords[nearest]
    nx, ny, nz = own[:, 0], own[:, 1], own[:, 2]
    wall = np.full(len(points), np.inf)
    for cx, cy, cz in coords:
        ex, ey, ez = cx - nx, cy - ny, cz - nz
        length = np.sqrt(ex * ex + ey * ey + ez * ez)
        valid = length > 0
        safe = np.where(valid, length, 1.0)
        mx, my, mz = (nx + cx) / 2, (ny + cy) / 2, (nz + cz) / 2
        d = np.abs(((px - mx) * ex + (py - my) * ey + (pz - mz) * ez) / safe)
        wall = np.where(valid, np.minimum(wall, d), wall)
    return wall, float(np.sqrt(best).max())


def _walls_dense(coords, points):
    """Wall distance for a flat list of points, vectorized over the seeds.

    The same field as :func:`_walls_flat`, in a handful of large NumPy calls
    instead of a few hundred small ones. That is slower on its own -- bigger
    intermediates, less cache reuse -- but it is what makes threaded sampling
    work: a call on a few million elements holds the GIL for milliseconds,
    where a call on a few thousand spends its life handing the GIL over. With
    the small-call formulation, ten threads came out an order of magnitude
    slower than one.

    Parameters
    ----------
    coords : :class:`numpy.ndarray`
        Candidate seeds, shape ``(k, 3)``.
    points : :class:`numpy.ndarray`
        Query points, shape ``(m, 3)``.

    Returns
    -------
    tuple[:class:`numpy.ndarray`, float]
        The wall distance per point, and the largest distance from a point to
        its own nearest seed.
    """
    import numpy as np

    rows = np.arange(len(points))
    best = np.full(len(points), np.inf)
    nearest = np.zeros(len(points), dtype=np.intp)
    for start in range(0, len(coords), _CHUNK):
        chunk = coords[start : start + _CHUNK]
        d2 = ((points[:, None, :] - chunk[None, :, :]) ** 2).sum(axis=-1)
        index = d2.argmin(axis=1)
        value = d2[rows, index]
        closer = value < best
        nearest = np.where(closer, index + start, nearest)
        best = np.where(closer, value, best)

    own = coords[nearest]
    wall = np.full(len(points), np.inf)
    for start in range(0, len(coords), _CHUNK):
        chunk = coords[start : start + _CHUNK]
        edge = chunk[None, :, :] - own[:, None, :]
        length = np.sqrt((edge * edge).sum(axis=-1))
        middle = (chunk[None, :, :] + own[:, None, :]) / 2
        valid = length > 0
        d = np.abs(((points[:, None, :] - middle) * edge).sum(axis=-1) / np.where(valid, length, 1.0))
        wall = np.minimum(wall, np.where(valid, d, np.inf).min(axis=1))
    return wall, float(np.sqrt(best).max())


def _formulation():
    """Which per-block formulation to use, and at what block size.

    Both compute the same field to the last bit; they differ only in how the
    work is shaped, and the right shape depends on whether this evaluation
    has a core to itself. Being called from a worker thread -- which is what
    :func:`compas_vol.meshing.sample` does by default -- means it does not.
    """
    import threading

    if threading.current_thread() is threading.main_thread():
        return _walls_flat, _BLOCK
    return _walls_dense, _BLOCK_THREADED


def _blocks(shape, block_size):
    """Index ranges covering the grid in blocks of at most ``block_size`` per axis."""
    import numpy as np

    axes = [
        [(int(a), int(b)) for a, b in zip(edges[:-1], edges[1:]) if b > a]
        for edges in (np.arange(0, n + block_size, block_size).clip(0, n) for n in shape)
    ]
    for i in axes[0]:
        for j in axes[1]:
            for k in axes[2]:
                yield (i, j, k)


def _slice(coordinates, axis, rows):
    """Slice a broadcastable coordinate array along one axis, if it spans it."""
    import numpy as np

    coordinates = np.asarray(coordinates)
    if coordinates.ndim == 3 and coordinates.shape[axis] > 1:
        index = [slice(None)] * 3
        index[axis] = slice(*rows)
        return coordinates[tuple(index)]
    return coordinates
