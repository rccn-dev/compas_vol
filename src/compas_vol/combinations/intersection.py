from compas_vol.base import VolObject
from compas_vol.base import reduce_distances


class Intersection(VolObject):
    """The Boolean intersection of two or more volumetric objects.

    Parameters
    ----------
    a : :class:`compas_vol.base.VolObject` | list
        The first object, or a list of objects. If ``a`` is a list, ``b`` is ignored.
    b : :class:`compas_vol.base.VolObject`, optional
        The second object.

    Examples
    --------
    >>> from compas.geometry import Box, Point, Sphere
    >>> from compas_vol.primitives import VolBox, VolSphere
    >>> from compas_vol.combinations import Intersection
    >>> vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> i = Intersection(vs, vb)
    >>> i.get_distance([5, 6, 0]) < 0
    True
    """

    def __init__(self, a=None, b=None, name=None):
        super().__init__(name=name)
        self.objs = list(a) if isinstance(a, (list, tuple)) else [a, b]

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"a": self.objs}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["a"])

    def __repr__(self):
        return "Intersection([{}])".format(", ".join(repr(o) for o in self.objs))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        return max(o.get_distance(point) for o in self.objs)

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        return reduce_distances(np.maximum, self.objs, x, y, z)
