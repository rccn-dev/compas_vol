from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances


class Union(VolObject):
    """The Boolean union of two or more volumetric objects.

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
    >>> from compas_vol.combinations import Union
    >>> vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
    >>> vb = VolBox(Box(20, 15, 10), 2.5)
    >>> u = Union(vs, vb)
    >>> u.get_distance([0, 0, 0]) < 0
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

    def add_object(self, o):
        """Add another object to the union."""
        self.objs.append(o)

    def __repr__(self):
        return "Union([{}])".format(", ".join(repr(o) for o in self.objs))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        return min(o.get_distance(point) for o in self.objs)

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        distances = [o.get_distance_numpy(x, y, z) for o in self.objs]
        return np.minimum.reduce(broadcast_distances(distances, x, y, z))
