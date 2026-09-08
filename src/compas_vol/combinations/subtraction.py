from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances


class Subtraction(VolObject):
    """The Boolean subtraction of one volumetric object from another.

    Parameters
    ----------
    a : :class:`compas_vol.base.VolObject`
        The object to subtract from.
    b : :class:`compas_vol.base.VolObject`
        The object to subtract.

    Examples
    --------
    >>> from compas.geometry import Box, Point, Sphere
    >>> from compas_vol.primitives import VolBox, VolSphere
    >>> from compas_vol.combinations import Subtraction
    >>> vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> s = Subtraction(vb, vs)
    >>> s.get_distance([5, 6, 0]) > 0
    True
    """

    def __init__(self, a=None, b=None, name=None):
        super().__init__(name=name)
        self.a = a
        self.b = b

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"a": self.a, "b": self.b}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["a"], data["b"])

    def __repr__(self):
        return "Subtraction({!r},{!r})".format(self.a, self.b)

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        return max(self.a.get_distance(point), -self.b.get_distance(point))

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        da, db = broadcast_distances(
            [self.a.get_distance_numpy(x, y, z), self.b.get_distance_numpy(x, y, z)], x, y, z
        )
        return np.maximum(da, -db)
