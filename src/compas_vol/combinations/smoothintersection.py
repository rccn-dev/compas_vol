from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances
from compas_vol.base import format_number


class SmoothIntersection(VolObject):
    """The smooth (filleted) intersection of two volumetric objects.

    Parameters
    ----------
    a, b : :class:`compas_vol.base.VolObject`
        The objects to intersect.
    r : float
        Intensity factor. The higher the number, the smoother the result.
        Default is ``1.0``.

    Examples
    --------
    >>> from compas.geometry import Box, Point, Sphere
    >>> from compas_vol.primitives import VolBox, VolSphere
    >>> from compas_vol.combinations import SmoothIntersection
    >>> vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> i = SmoothIntersection(vs, vb, 1.5)
    >>> i.get_distance([5, 6, 0]) < 0
    True
    """

    def __init__(self, a=None, b=None, r=1.0, name=None):
        super().__init__(name=name)
        self.a = a
        self.b = b
        self.r = r

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"a": self.a, "b": self.b, "r": self.r}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["a"], data["b"], data["r"])

    def __repr__(self):
        return "SmoothIntersection({0!r},{1!r},{2})".format(self.a, self.b, format_number(self.r))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        da = self.a.get_distance(point)
        db = self.b.get_distance(point)
        k = self.r
        h = min(max(0.5 - 0.5 * (db - da) / k, 0), 1)
        return (db * (1 - h) + h * da) + k * h * (1 - h)

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        da, db = broadcast_distances(
            [self.a.get_distance_numpy(x, y, z), self.b.get_distance_numpy(x, y, z)], x, y, z
        )
        h = np.clip(0.5 - 0.5 * (db - da) / self.r, 0, 1)
        return (db * (1 - h) + h * da) + self.r * h * (1 - h)
