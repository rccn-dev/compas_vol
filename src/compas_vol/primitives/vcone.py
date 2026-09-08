from compas.geometry import Cone
from compas.geometry import length_vector_xy

from compas_vol.base import VolObject
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy


class VolCone(VolObject):
    """A volumetric cone, defined by a :class:`compas.geometry.Cone`.

    The cone tapers from ``radius`` at its base to a point at the top, and is
    centred on the origin of its own frame.

    Parameters
    ----------
    cone : :class:`compas.geometry.Cone`
        The base cone.

    Examples
    --------
    >>> from compas.geometry import Cone
    >>> from compas_vol.primitives import VolCone
    >>> vcone = VolCone(Cone(5, 7))
    >>> round(vcone.get_distance([0, 0, 0]), 6)
    -2.5
    """

    def __init__(self, cone, name=None):
        super().__init__(name=name)
        self._cone = None
        self.inversetransform = None
        self.cone = cone

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"cone": self.cone.__data__}

    @classmethod
    def __from_data__(cls, data):
        return cls(Cone.__from_data__(data["cone"]))

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def cone(self):
        return self._cone

    @cone.setter
    def cone(self, cone):
        if not isinstance(cone, Cone):
            raise TypeError("Expected a compas.geometry.Cone, got {}".format(type(cone).__name__))
        self._cone = cone
        # COMPAS 2 removed ``Cone.plane``; the shape's own frame replaces it.
        self.inversetransform = inverse_matrix_from_frame(cone.frame)

    def __repr__(self):
        return "VolCone({!r})".format(self.cone)

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)

        f = (p.z + self.cone.height / 2) / self.cone.height
        temprad = self.cone.radius - f * self.cone.radius
        dxy = length_vector_xy(p) - temprad
        return max(dxy, abs(p.z) - self.cone.height / 2)

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)

        f = (zt + self.cone.height / 2) / self.cone.height
        temprad = self.cone.radius - f * self.cone.radius
        dxy = np.sqrt(xt * xt + yt * yt) - temprad
        return np.maximum(dxy, np.abs(zt) - self.cone.height / 2)
