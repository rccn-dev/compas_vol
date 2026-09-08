from compas.geometry import closest_point_on_segment

from compas_vol.base import VolObject
from compas_vol.base import format_number


class VolCapsule(VolObject):
    """A volumetric capsule, defined by a line segment and a radius.

    Parameters
    ----------
    segment : tuple[point, point]
        Start and end point of the line segment.
    radius : float
        The radius of the capsule.

    Examples
    --------
    >>> from compas_vol.primitives import VolCapsule
    >>> capsule = VolCapsule(((1, 2, -3), (5, 4, 3)), 3.0)
    >>> round(capsule.get_distance([1, 2, -3]), 6)
    -3.0
    """

    def __init__(self, segment, radius, name=None):
        super().__init__(name=name)
        self.segment = segment
        self.radius = radius

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "segment": [list(self.segment[0]), list(self.segment[1])],
            "radius": self.radius,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(tuple(tuple(p) for p in data["segment"]), data["radius"])

    def __repr__(self):
        a, b = self.segment
        return "VolCapsule(({0}, {1}), {2})".format(tuple(a), tuple(b), format_number(self.radius))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        closest = closest_point_on_segment(p, self.segment)
        return p.distance_to_point(closest) - self.radius

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        ax, ay, az = (float(c) for c in self.segment[0])
        bx, by, bz = (float(c) for c in self.segment[1])

        # Vector from the segment start to every query point.
        px = x - ax
        py = y - ay
        pz = z - az

        # The segment direction, and the parameter of the closest point on it.
        ex, ey, ez = bx - ax, by - ay, bz - az
        ee = ex * ex + ey * ey + ez * ez
        h = np.clip((px * ex + py * ey + pz * ez) / ee, 0.0, 1.0)

        dx = px - ex * h
        dy = py - ey * h
        dz = pz - ez * h
        return np.sqrt(dx * dx + dy * dy + dz * dz) - self.radius
