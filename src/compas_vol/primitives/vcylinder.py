from compas.geometry import Cylinder
from compas.geometry import length_vector_xy

from compas_vol.base import VolObject
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy


class VolCylinder(VolObject):
    """A volumetric cylinder, defined by a :class:`compas.geometry.Cylinder`.

    Parameters
    ----------
    cylinder : :class:`compas.geometry.Cylinder`
        The base cylinder.

    Examples
    --------
    >>> from compas.geometry import Cylinder
    >>> from compas_vol.primitives import VolCylinder
    >>> vcylinder = VolCylinder(Cylinder(5, 7))
    >>> round(vcylinder.get_distance([0, 0, 0]), 6)
    -3.5
    """

    def __init__(self, cylinder, name=None):
        super().__init__(name=name)
        self._cylinder = None
        self.inversetransform = None
        self.cylinder = cylinder

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"cylinder": self.cylinder.__data__}

    @classmethod
    def __from_data__(cls, data):
        return cls(Cylinder.__from_data__(data["cylinder"]))

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def cylinder(self):
        return self._cylinder

    @cylinder.setter
    def cylinder(self, cylinder):
        if not isinstance(cylinder, Cylinder):
            raise TypeError("Expected a compas.geometry.Cylinder, got {}".format(type(cylinder).__name__))
        self._cylinder = cylinder
        # COMPAS 2 shapes carry their own frame, so there is no need to rebuild
        # one from a plane the way COMPAS 1 required.
        self.inversetransform = inverse_matrix_from_frame(cylinder.frame)

    def __repr__(self):
        return "VolCylinder({!r})".format(self.cylinder)

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)

        d = length_vector_xy(p) - self.cylinder.radius
        return max(d, abs(p.z) - self.cylinder.height / 2.0)

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)

        d = np.sqrt(xt * xt + yt * yt) - self.cylinder.radius
        return np.maximum(d, np.abs(zt) - self.cylinder.height / 2.0)
