from compas.geometry import Plane
from compas.geometry import distance_point_plane_signed

from compas_vol.base import VolObject


class VolPlane(VolObject):
    """A volumetric half-space, defined by a :class:`compas.geometry.Plane`.

    Points on the side the normal points to are outside (positive distance).

    Parameters
    ----------
    plane : :class:`compas.geometry.Plane`
        The base plane.

    Examples
    --------
    >>> from compas.geometry import Plane
    >>> from compas_vol.primitives import VolPlane
    >>> vplane = VolPlane(Plane([0, 0, 0], [0, 0, 1]))
    >>> round(vplane.get_distance([3, 4, 5]), 6)
    5.0
    """

    def __init__(self, plane, name=None):
        super().__init__(name=name)
        self._plane = None
        self.plane = plane

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"plane": self.plane.__data__}

    @classmethod
    def __from_data__(cls, data):
        return cls(Plane.__from_data__(data["plane"]))

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def plane(self):
        return self._plane

    @plane.setter
    def plane(self, plane):
        if not isinstance(plane, Plane):
            plane = Plane(*plane)
        self._plane = plane

    def __repr__(self):
        return "VolPlane({!r})".format(self.plane)

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        return distance_point_plane_signed(point, self.plane)

    def get_distance_numpy(self, x, y, z):
        base = self.plane.point
        nx, ny, nz = self.plane.normal
        return (x - base.x) * nx + (y - base.y) * ny + (z - base.z) * nz
