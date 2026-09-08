from compas.geometry import Point
from compas.geometry import Vector

from compas_vol.base import format_number


class Gradient(object):
    """The gradient (nabla) of a distance function.

    The gradient points away from the surface, and is perpendicular to the
    zero level set for points on the boundary. For a true signed distance
    field it is a unit vector everywhere.

    Parameters
    ----------
    o : :class:`compas_vol.base.VolObject`
        The object whose signed distance function to differentiate.
    e : float
        Epsilon, the offset used for the central difference.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.analysis import Gradient
    >>> g = Gradient(VolSphere(Sphere(5, point=Point(0, 0, 0))))
    >>> v = g.get_gradient(Point(5, 0, 0))
    >>> round(v.x, 3), round(v.y, 3), round(v.z, 3)
    (1.0, 0.0, 0.0)
    """

    def __init__(self, o, e=0.01):
        self.o = o
        self.e = e

    def __repr__(self):
        return "Gradient({0!r},{1})".format(self.o, format_number(self.e))

    def get_gradient_regular(self, point):
        """Central-difference gradient, sampling six neighbours."""
        p = Point(*point)
        e = self.e
        dx = self.o.get_distance((p.x + e, p.y, p.z)) - self.o.get_distance((p.x - e, p.y, p.z))
        dy = self.o.get_distance((p.x, p.y + e, p.z)) - self.o.get_distance((p.x, p.y - e, p.z))
        dz = self.o.get_distance((p.x, p.y, p.z + e)) - self.o.get_distance((p.x, p.y, p.z - e))
        v = Vector(dx, dy, dz)
        v.unitize()
        return v

    def get_gradient(self, point):
        """Central differences on a tetrahedron, sampling only four neighbours.

        30-40% faster than :meth:`get_gradient_regular`.
        """
        p = Point(*point)
        e = self.e
        d0 = self.o.get_distance(Point(p.x + e, p.y - e, p.z - e))
        d1 = self.o.get_distance(Point(p.x - e, p.y - e, p.z + e))
        d2 = self.o.get_distance(Point(p.x - e, p.y + e, p.z - e))
        d3 = self.o.get_distance(Point(p.x + e, p.y + e, p.z + e))
        v = Vector(d0 - d1 - d2 + d3, -d0 - d1 + d2 + d3, -d0 + d1 - d2 + d3)
        v.unitize()
        return v

    def get_gradient_numpy(self, x, y, z):
        """Vectorized tetrahedron-difference gradient.

        Returns
        -------
        :class:`numpy.ndarray`
            Unit gradient vectors, of shape ``(nx, ny, nz, 3)``.
        """
        import numpy as np

        e = self.e
        d0 = self.o.get_distance_numpy(x + e, y - e, z - e)
        d1 = self.o.get_distance_numpy(x - e, y - e, z + e)
        d2 = self.o.get_distance_numpy(x - e, y + e, z - e)
        d3 = self.o.get_distance_numpy(x + e, y + e, z + e)

        # The old version built the vector field by multiplying (3,) constant
        # arrays against (nx, ny, nz) distances, then divided by a norm taken
        # over axis 3 without re-inserting the reduced axis, so it either
        # raised or broadcast wrongly. Stacking on the last axis makes the
        # vector component axis explicit.
        v = np.stack(
            [d0 - d1 - d2 + d3, -d0 - d1 + d2 + d3, -d0 + d1 - d2 + d3],
            axis=-1,
        )
        norm = np.linalg.norm(v, axis=-1, keepdims=True)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(norm == 0, 0.0, v / norm)
