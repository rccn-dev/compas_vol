from math import cos
from math import sin

from compas.geometry import Frame

from compas_vol.base import VolObject
from compas_vol.base import format_number


class Twist(VolObject):
    """Twist a volumetric object around the normal axis of a frame.

    The query point is rotated about the frame's normal by an angle
    proportional to its signed distance along that axis, which shears the
    object into a helix.

    In COMPAS 1 the two distance methods disagreed: the single-point version
    rotated by ``distance / 10`` while the vectorized version applied a single
    fixed 10-radian rotation to every point. Both ignored ``self.angle``
    entirely. Both now honour :attr:`angle`.

    Parameters
    ----------
    obj : :class:`compas_vol.base.VolObject`
        The object to twist.
    frame : :class:`compas.geometry.Frame`, optional
        The frame whose normal is the twist axis. Defaults to the world XY frame.
    angle : float
        The twist rate, in radians per unit length along the axis.

    Examples
    --------
    >>> from compas.geometry import Box
    >>> from compas_vol.primitives import VolBox
    >>> from compas_vol.modifications import Twist
    >>> vb = VolBox(Box(20, 15, 10), 1.5)
    >>> t = Twist(vb, angle=0.1)
    >>> round(t.get_distance([0, 0, 0]), 6)
    -5.0
    """

    def __init__(self, obj, frame=None, angle=0.0, name=None):
        super().__init__(name=name)
        self.obj = obj
        self.frame = frame or Frame.worldXY()
        self.angle = angle

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"obj": self.obj, "frame": self.frame.__data__, "angle": self.angle}

    @classmethod
    def __from_data__(cls, data):
        return cls(data["obj"], Frame.__from_data__(data["frame"]), data["angle"])

    def __repr__(self):
        return "Twist({0!r},{1!r},{2})".format(self.obj, self.frame, format_number(self.angle))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        o = self.frame.point
        k = self.frame.normal

        vx, vy, vz = p.x - o.x, p.y - o.y, p.z - o.z
        # Signed height along the axis drives the rotation angle.
        h = vx * k.x + vy * k.y + vz * k.z
        theta = -self.angle * h
        c, s = cos(theta), sin(theta)

        # Rodrigues' rotation of v about the unit axis k.
        cx = k.y * vz - k.z * vy
        cy = k.z * vx - k.x * vz
        cz = k.x * vy - k.y * vx
        rx = vx * c + cx * s + k.x * h * (1 - c)
        ry = vy * c + cy * s + k.y * h * (1 - c)
        rz = vz * c + cz * s + k.z * h * (1 - c)

        return self.obj.get_distance((o.x + rx, o.y + ry, o.z + rz))

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        o = self.frame.point
        k = self.frame.normal

        vx = x - o.x
        vy = y - o.y
        vz = z - o.z

        h = vx * k.x + vy * k.y + vz * k.z
        theta = -self.angle * h
        c, s = np.cos(theta), np.sin(theta)

        cx = k.y * vz - k.z * vy
        cy = k.z * vx - k.x * vz
        cz = k.x * vy - k.y * vx
        rx = vx * c + cx * s + k.x * h * (1 - c)
        ry = vy * c + cy * s + k.y * h * (1 - c)
        rz = vz * c + cz * s + k.z * h * (1 - c)

        return self.obj.get_distance_numpy(o.x + rx, o.y + ry, o.z + rz)
