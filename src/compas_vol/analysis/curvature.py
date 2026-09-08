from compas.geometry import Point

from compas_vol.base import format_number


class Curvature(object):
    """The mean curvature of the level sets of a distance function.

    For a signed distance field the divergence of the gradient -- the
    Laplacian -- equals twice the mean curvature of the level set through each
    point. Positive values indicate a locally convex surface, negative a
    concave one.

    In COMPAS 1 this class had an empty ``__init__`` and no distance methods at
    all.

    Parameters
    ----------
    o : :class:`compas_vol.base.VolObject`
        The object whose signed distance function to analyse.
    e : float
        Epsilon, the offset used for the finite differences.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.analysis import Curvature
    >>> c = Curvature(VolSphere(Sphere(5, point=Point(0, 0, 0))), e=0.1)
    >>> # a sphere of radius 5 has mean curvature 1/5 at its surface
    >>> round(c.get_curvature(Point(5, 0, 0)), 2)
    0.2
    """

    def __init__(self, o, e=0.01):
        self.o = o
        self.e = e

    def __repr__(self):
        return "Curvature({0!r},{1})".format(self.o, format_number(self.e))

    def get_curvature(self, point):
        """The mean curvature of the level set through a single point."""
        p = Point(*point)
        e = self.e
        d = self.o.get_distance(p)

        laplacian = (
            self.o.get_distance((p.x + e, p.y, p.z))
            + self.o.get_distance((p.x - e, p.y, p.z))
            + self.o.get_distance((p.x, p.y + e, p.z))
            + self.o.get_distance((p.x, p.y - e, p.z))
            + self.o.get_distance((p.x, p.y, p.z + e))
            + self.o.get_distance((p.x, p.y, p.z - e))
            - 6 * d
        ) / (e * e)
        return laplacian / 2.0

    def get_curvature_numpy(self, x, y, z):
        """The mean curvature over a grid.

        Returns
        -------
        :class:`numpy.ndarray`
            Mean curvature values, of shape ``(nx, ny, nz)``.
        """
        e = self.e
        d = self.o.get_distance_numpy(x, y, z)

        laplacian = (
            self.o.get_distance_numpy(x + e, y, z)
            + self.o.get_distance_numpy(x - e, y, z)
            + self.o.get_distance_numpy(x, y + e, z)
            + self.o.get_distance_numpy(x, y - e, z)
            + self.o.get_distance_numpy(x, y, z + e)
            + self.o.get_distance_numpy(x, y, z - e)
            - 6 * d
        ) / (e * e)
        return laplacian / 2.0
