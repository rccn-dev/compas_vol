from math import sqrt

from compas.geometry import Torus
from compas.geometry import length_vector_xy

from compas_vol.base import VolObject
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy


class VolTorus(VolObject):
    """A volumetric torus, defined by a :class:`compas.geometry.Torus`.

    Parameters
    ----------
    torus : :class:`compas.geometry.Torus`
        The base torus.

    Examples
    --------
    >>> from compas.geometry import Torus
    >>> from compas_vol.primitives import VolTorus
    >>> vtorus = VolTorus(Torus(5.0, 2.0))
    >>> round(vtorus.get_distance([5, 0, 0]), 6)
    -2.0
    """

    def __init__(self, torus, name=None):
        super().__init__(name=name)
        self._torus = None
        self.inversetransform = None
        self.torus = torus

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"torus": self.torus.__data__}

    @classmethod
    def __from_data__(cls, data):
        return cls(Torus.__from_data__(data["torus"]))

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def torus(self):
        return self._torus

    @torus.setter
    def torus(self, torus):
        if not isinstance(torus, Torus):
            raise TypeError("Expected a compas.geometry.Torus, got {}".format(type(torus).__name__))
        self._torus = torus
        self.inversetransform = inverse_matrix_from_frame(torus.frame)

    def __repr__(self):
        return "VolTorus({!r})".format(self.torus)

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)

        dxy = length_vector_xy(p)
        d2 = sqrt((dxy - self.torus.radius_axis) ** 2 + p.z**2)
        return d2 - self.torus.radius_pipe

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)

        d = np.sqrt(xt**2 + yt**2) - self.torus.radius_axis
        d2 = np.sqrt(d**2 + zt**2)
        return d2 - self.torus.radius_pipe
