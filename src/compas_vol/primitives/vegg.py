from compas.geometry import Frame

from compas_vol.base import VolObject
from compas_vol.base import format_number
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy


class VolEgg(VolObject):
    """An egg shape: an ellipsoid tapered along its local Z axis.

    Note that this is a scalar field rather than a true signed distance
    field -- the zero level set is the egg's surface, but the gradient is not
    unit length, so offsets and shells will not be metrically accurate.

    Parameters
    ----------
    radiusA : float
        The radius in the local XY plane.
    radiusB : float
        The radius along the local Z axis.
    k : float
        The taper factor. At ``k = 0`` the shape is a plain ellipsoid.
    frame : :class:`compas.geometry.Frame`, optional
        The base frame. Defaults to the world XY frame.

    Examples
    --------
    >>> from compas_vol.primitives import VolEgg
    >>> egg = VolEgg(3, 4, 0.1)
    >>> round(egg.get_distance([0, 0, 0]), 6)
    -1.0
    """

    def __init__(self, radiusA=3, radiusB=4, k=0.1, frame=None, name=None):
        super().__init__(name=name)
        self._frame = None
        self.inversetransform = None
        self.ra = radiusA
        self.rb = radiusB
        self.k = k
        self.frame = frame or Frame.worldXY()

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "radiusA": self.ra,
            "radiusB": self.rb,
            "k": self.k,
            "frame": self.frame.__data__,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(data["radiusA"], data["radiusB"], data["k"], Frame.__from_data__(data["frame"]))

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
        return "VolEgg({0},{1},{2},{3!r})".format(
            format_number(self.ra), format_number(self.rb), format_number(self.k), self.frame
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)

        return (
            (p.z * p.z) / (self.rb * self.rb)
            + (p.y * p.y) / (self.ra * self.ra)
            + (p.x * p.x) / (self.ra * self.ra) * (1 + self.k * p.z)
            - 1
        )

    def get_distance_numpy(self, x, y, z):
        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)

        return (
            (zt * zt) / (self.rb * self.rb)
            + (yt * yt) / (self.ra * self.ra)
            + (xt * xt) / (self.ra * self.ra) * (1 + self.k * zt)
            - 1
        )
