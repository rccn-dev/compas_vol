from math import pi
from math import sqrt
from math import tan

from compas.geometry import Frame

from compas_vol.base import VolObject
from compas_vol.base import format_number
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy

# The normalised (phi, 1, 0) vector shared by the dodecahedron faces.
_PHI = (1 + sqrt(5)) / 2
_DODEC = tuple(c / sqrt(_PHI**2 + 1) for c in (_PHI, 1.0, 0.0))

# The equivalent for the icosahedron.
_ICO_RAW = ((sqrt(5) + 3) / 2, 1.0, 0.0)
_ICO = tuple(c / sqrt(_ICO_RAW[0] ** 2 + 1) for c in _ICO_RAW)
_ICO_R = 0.8506507174597755
_W = sqrt(3) / 3


class PlatonicSolid(VolObject):
    """A platonic solid, defined by a radius and a type.

    Parameters
    ----------
    radius : float
        The radius of the solid.
    solid_type : int
        ``0`` tetrahedron, ``1`` octahedron, ``2`` dodecahedron, ``3`` icosahedron.
        This argument was called ``type`` in COMPAS 1, which shadowed the
        builtin; positional use is unchanged.
    frame : :class:`compas.geometry.Frame`, optional
        The base frame. Defaults to the world XY frame.

    Examples
    --------
    >>> from compas_vol.primitives import PlatonicSolid
    >>> p = PlatonicSolid(10.0, 1)
    >>> p.get_distance([0, 0, 0]) < 0
    True

    References
    ----------
    Adapted from the SDF library by Michael Fogleman [1]_

    .. [1] https://github.com/fogleman/sdf/blob/main/sdf/d3.py#L283
    """

    TYPENAMES = {0: "tetrahedron", 1: "octahedron", 2: "dodecahedron", 3: "icosahedron"}

    def __init__(self, radius, solid_type=0, frame=None, name=None):
        super().__init__(name=name)
        self._frame = None
        self.inversetransform = None
        self.radius = radius
        self.solid_type = solid_type
        self.frame = frame or Frame.worldXY()
        self.sqrt3 = sqrt(3)
        self.tan30 = tan(pi / 6)

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "radius": self.radius,
            "solid_type": self.solid_type,
            "frame": self.frame.__data__,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(data["radius"], data["solid_type"], Frame.__from_data__(data["frame"]))

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

    @property
    def typename(self):
        return self.TYPENAMES.get(self.solid_type, "unknown")

    def __repr__(self):
        return "PlatonicSolid({0},{1},{2!r})".format(
            format_number(self.radius), self.solid_type, self.frame
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)
        x, y, z = p.x, p.y, p.z

        # Tetrahedron
        if self.solid_type == 0:
            return (max(abs(x + y) - z, abs(x - y) + z) - self.radius) / self.sqrt3

        # Octahedron
        if self.solid_type == 1:
            return (abs(x) + abs(y) + abs(z) - self.radius) * self.tan30

        # Dodecahedron
        if self.solid_type == 2:
            vx, vy, vz = _DODEC
            px, py, pz = abs(x / self.radius), abs(y / self.radius), abs(z / self.radius)
            a = px * vx + py * vy + pz * vz
            b = px * vz + py * vx + pz * vy
            c = px * vy + py * vz + pz * vx
            return (max(a, b, c) - vx) * self.radius

        # Icosahedron
        if self.solid_type == 3:
            r = self.radius * _ICO_R
            vx, vy, vz = _ICO
            px, py, pz = abs(x / r), abs(y / r), abs(z / r)
            a = px * vx + py * vy + pz * vz
            b = px * vz + py * vx + pz * vy
            c = px * vy + py * vz + pz * vx
            d = (px + py + pz) * _W - vx
            return max(max(a, b, c) - vx, d) * r

        return 0.0

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)

        # Tetrahedron
        if self.solid_type == 0:
            return (
                np.maximum(np.abs(xt + yt) - zt, np.abs(xt - yt) + zt) - self.radius
            ) / self.sqrt3

        # Octahedron
        if self.solid_type == 1:
            return (np.abs(xt) + np.abs(yt) + np.abs(zt) - self.radius) * self.tan30

        # Dodecahedron
        if self.solid_type == 2:
            vx, vy, vz = _DODEC
            px, py, pz = np.abs(xt / self.radius), np.abs(yt / self.radius), np.abs(zt / self.radius)
            a = px * vx + py * vy + pz * vz
            b = px * vz + py * vx + pz * vy
            c = px * vy + py * vz + pz * vx
            return (np.maximum(np.maximum(a, b), c) - vx) * self.radius

        # Icosahedron
        if self.solid_type == 3:
            r = self.radius * _ICO_R
            vx, vy, vz = _ICO
            px, py, pz = np.abs(xt / r), np.abs(yt / r), np.abs(zt / r)
            a = px * vx + py * vy + pz * vz
            b = px * vz + py * vx + pz * vy
            c = px * vy + py * vz + pz * vx
            d = (px + py + pz) * _W - vx
            return np.maximum(np.maximum(np.maximum(a, b), c) - vx, d) * r

        shape = np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z))
        return np.zeros(shape)
