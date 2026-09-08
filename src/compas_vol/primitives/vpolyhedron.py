from compas_vol.base import VolObject
from compas_vol.base import broadcast_distances

from .vplane import VolPlane


class VolPolyhedron(VolObject):
    """A convex polyhedron, delimited by a list of planes.

    The solid is the intersection of the half-spaces defined by the planes, so
    every normal must point away from the interior.

    Parameters
    ----------
    planes : list[:class:`compas_vol.primitives.VolPlane`]
        The delimiting planes.

    Examples
    --------
    >>> import math
    >>> from compas.geometry import Plane
    >>> from compas_vol.primitives import VolPlane, VolPolyhedron
    >>> planes = []
    >>> for i in range(7):
    ...     a = math.pi * 2 * i / 7
    ...     x, y = math.cos(a), math.sin(a)
    ...     planes.append(VolPlane(Plane((9 * x, 9 * y, 0), (x, y, 0))))
    >>> vh = VolPolyhedron(planes)
    >>> round(vh.get_distance([0, 0, 0]), 6)
    -9.0
    """

    def __init__(self, planes=None, name=None):
        super().__init__(name=name)
        self.planes = list(planes) if planes else []

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"planes": [p.__data__ for p in self.planes]}

    @classmethod
    def __from_data__(cls, data):
        return cls([VolPlane.__from_data__(d) for d in data["planes"]])

    def __repr__(self):
        return "VolPolyhedron([{}])".format(", ".join(repr(p) for p in self.planes))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        return max(p.get_distance(point) for p in self.planes)

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        distances = [p.get_distance_numpy(x, y, z) for p in self.planes]
        return np.maximum.reduce(broadcast_distances(distances, x, y, z))
