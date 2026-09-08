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

        coords = np.asarray(self.points, dtype=float)  # (m, 3)
        shape = np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z))
        px, py, pz = (np.broadcast_to(c, shape) for c in (x, y, z))

        # Looping over seeds keeps peak memory at O(grid) instead of the
        # O(grid * seeds) a fully broadcast (..., m) formulation needs. At
        # 160^3 with 120 seeds the broadcast version wants tens of gigabytes.

        # Pass one: which cell does each grid point belong to?
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

        # Pass two: distance to the nearest bisecting plane between that cell's
        # seed and any other one.
        best = np.full(shape, np.inf)
        for cx, cy, cz in coords:
            ex, ey, ez = cx - nx, cy - ny, cz - nz
            length = np.sqrt(ex * ex + ey * ey + ez * ez)
            # length == 0 is the seed's bisector with itself, which is degenerate.
            valid = length > 0
            safe = np.where(valid, length, 1.0)
            mx, my, mz = (nx + cx) / 2, (ny + cy) / 2, (nz + cz) / 2
            d = np.abs(((px - mx) * ex + (py - my) * ey + (pz - mz) * ez) / safe)
            best = np.where(valid, np.minimum(best, d), best)

        if not self.walls:
            return self.thickness / 2 - best
        return best - self.thickness / 2
