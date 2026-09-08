from math import log

from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances
from compas_vol.base import format_number


class SmoothUnionList(VolObject):
    """The exponential smooth union of a list of volumetric objects.

    Unlike chaining :class:`SmoothUnion` pairwise, this blends all objects at
    once, so the result does not depend on the order they are given in.

    Parameters
    ----------
    a : list[:class:`compas_vol.base.VolObject`]
        The objects to add.
    k : float
        Intensity factor. The *smaller* the number, the stronger the smoothing.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> from compas_vol.combinations import SmoothUnionList
    >>> spheres = [VolSphere(Sphere(4, point=Point(i * 5, 0, 0))) for i in range(3)]
    >>> u = SmoothUnionList(spheres, 1.0)
    >>> u.get_distance([0, 0, 0]) < 0
    True
    """

    def __init__(self, a=None, k=1.0, name=None):
        super().__init__(name=name)
        self.distance_objects = list(a) if a else []
        self.k = k

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"a": self.distance_objects, "k": self.k}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["a"], data["k"])

    def __repr__(self):
        return "SmoothUnionList([{0}],{1})".format(
            ", ".join(repr(o) for o in self.distance_objects), format_number(self.k)
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        res = sum(pow(2, -self.k * o.get_distance(point)) for o in self.distance_objects)
        return -log(res, 2) / self.k

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        distances = [o.get_distance_numpy(x, y, z) for o in self.distance_objects]
        # The previous implementation transposed the stack and then summed over
        # axis 3, which reduced the wrong axis and returned a grid with its x
        # and z axes swapped. Stacking on axis 0 and reducing that axis keeps
        # the grid orientation intact.
        stacked = np.stack(broadcast_distances(distances, x, y, z), axis=0)
        res = np.sum(np.exp2(-self.k * stacked), axis=0)
        return -np.log2(res) / self.k
