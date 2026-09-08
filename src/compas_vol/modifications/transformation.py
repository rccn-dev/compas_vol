from compas.geometry import Frame

from compas_vol.base import VolObject
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy


class VolTransformation(VolObject):
    """Relocate a volumetric object into the coordinate system of a frame.

    Parameters
    ----------
    distobj : :class:`compas_vol.base.VolObject`
        The object to transform.
    frame : :class:`compas.geometry.Frame`, optional
        The target frame. Defaults to the world XY frame.

    Examples
    --------
    >>> from compas.geometry import Box, Frame
    >>> from compas_vol.primitives import VolBox
    >>> from compas_vol.modifications import VolTransformation
    >>> vb = VolBox(Box(20, 15, 10), 1.5)
    >>> t = VolTransformation(vb, Frame((5, 0, 0), (1, 0, 0), (0, 1, 0)))
    >>> round(t.get_distance([5, 0, 0]), 6)
    -5.0
    """

    def __init__(self, distobj=None, frame=None, name=None):
        super().__init__(name=name)
        self._frame = None
        self.inversetransform = None
        self.distobj = distobj
        self.frame = frame or Frame.worldXY()

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"distobj": self.distobj, "frame": self.frame.__data__}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["distobj"], Frame.__from_data__(data["frame"]))

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def frame(self):
        return self._frame

    @frame.setter
    def frame(self, frame):
        self._frame = frame
        self.inversetransform = inverse_matrix_from_frame(frame)

    def __repr__(self):
        return "VolTransformation({0!r},{1!r})".format(self.distobj, self.frame)

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)
        return self.distobj.get_distance(p)

    def get_distance_numpy(self, x, y, z):
        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)
        return self.distobj.get_distance_numpy(xt, yt, zt)
