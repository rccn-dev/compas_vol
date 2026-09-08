from compas.geometry import Sphere

from compas_vol.base import VolObject


class VolSphere(VolObject):
    """A volumetric sphere, defined by a :class:`compas.geometry.Sphere`.

    Parameters
    ----------
    sphere : :class:`compas.geometry.Sphere`
        The base sphere.

    Examples
    --------
    >>> from compas.geometry import Point, Sphere
    >>> from compas_vol.primitives import VolSphere
    >>> vs = VolSphere(Sphere(5, point=Point(1, 1, 1)))
    >>> round(vs.get_distance([1, 1, 1]), 6)
    -5.0
    """

    def __init__(self, sphere, name=None):
        super().__init__(name=name)
        self._sphere = None
        self.sphere = sphere

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"sphere": self.sphere.__data__}

    @classmethod
    def __from_data__(cls, data):
        return cls(Sphere.__from_data__(data["sphere"]))

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def sphere(self):
        return self._sphere

    @sphere.setter
    def sphere(self, sphere):
        if not isinstance(sphere, Sphere):
            raise TypeError("Expected a compas.geometry.Sphere, got {}".format(type(sphere).__name__))
        self._sphere = sphere

    @property
    def center(self):
        """:class:`compas.geometry.Point`: The centre of the sphere.

        COMPAS 2 dropped ``Sphere.center`` in favour of ``Sphere.base`` (which
        is ``frame.point``); this keeps the familiar name available.
        """
        return self.sphere.frame.point

    def __repr__(self):
        return "VolSphere({!r})".format(self.sphere)

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        return p.distance_to_point(self.center) - self.sphere.radius

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        c = self.center
        return np.sqrt((x - c.x) ** 2 + (y - c.y) ** 2 + (z - c.z) ** 2) - self.sphere.radius
