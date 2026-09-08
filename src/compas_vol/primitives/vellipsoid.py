from compas.geometry import Frame
from compas.geometry import Vector

from compas_vol.base import VolObject
from compas_vol.base import format_number
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy


class VolEllipsoid(VolObject):
    """A volumetric ellipsoid, defined by three radii along its local axes.

    Parameters
    ----------
    radiusX, radiusY, radiusZ : float
        The radii along the local X, Y and Z axes.
    frame : :class:`compas.geometry.Frame`, optional
        The base frame. Defaults to the world XY frame.

    Examples
    --------
    >>> from compas_vol.primitives import VolEllipsoid
    >>> e = VolEllipsoid(14, 10, 6)
    >>> round(e.get_distance([14, 0, 0]), 6)
    0.0
    """

    def __init__(self, radiusX=3, radiusY=2, radiusZ=1, frame=None, name=None):
        super().__init__(name=name)
        self._frame = None
        self.inversetransform = None
        self.radiusX = radiusX
        self.radiusY = radiusY
        self.radiusZ = radiusZ
        self.frame = frame or Frame.worldXY()

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "radiusX": self.radiusX,
            "radiusY": self.radiusY,
            "radiusZ": self.radiusZ,
            "frame": self.frame.__data__,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(
            data["radiusX"],
            data["radiusY"],
            data["radiusZ"],
            Frame.__from_data__(data["frame"]),
        )

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
        return "VolEllipsoid({0},{1},{2},{3!r})".format(
            format_number(self.radiusX),
            format_number(self.radiusY),
            format_number(self.radiusZ),
            self.frame,
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)

        k0 = Vector(p.x / self.radiusX, p.y / self.radiusY, p.z / self.radiusZ).length
        k1 = Vector(p.x / self.radiusX**2, p.y / self.radiusY**2, p.z / self.radiusZ**2).length
        if k1 == 0:
            return -min(self.radiusX, self.radiusY, self.radiusZ)
        return k0 * (k0 - 1.0) / k1

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)

        k0 = np.sqrt(
            np.square(xt / self.radiusX) + np.square(yt / self.radiusY) + np.square(zt / self.radiusZ)
        )
        k1 = np.sqrt(
            np.square(xt / self.radiusX**2)
            + np.square(yt / self.radiusY**2)
            + np.square(zt / self.radiusZ**2)
        )
        # Guard the division so the k1 == 0 branch does not emit a warning.
        safe = np.where(k1 == 0, 1.0, k1)
        inner = -min(self.radiusX, self.radiusY, self.radiusZ)
        return np.where(k1 == 0, inner, k0 * (k0 - 1.0) / safe)
