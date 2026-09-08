from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances


class Addition(VolObject):
    """The sum of the scalar fields of two or more volumetric objects.

    Note that adding distance fields does not generally produce a valid
    distance field; the result is a scalar field whose zero level set is still
    meaningful, but whose gradient is not unit length.

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
    >>> from compas_vol.combinations import Addition
    >>> vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> a = Addition(vs, vb)
    >>> isinstance(a.get_distance([0, 0, 0]), float)
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
        return "Addition([{}])".format(", ".join(repr(o) for o in self.objs))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        return sum(o.get_distance(point) for o in self.objs)

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        distances = [o.get_distance_numpy(x, y, z) for o in self.objs]
        return np.sum(broadcast_distances(distances, x, y, z), axis=0)
