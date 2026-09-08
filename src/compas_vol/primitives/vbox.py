from math import pi
from math import sqrt

from compas.geometry import Box

from compas_vol.base import VolObject
from compas_vol.base import format_number
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy


class VolBox(VolObject):
    """A volumetric box, defined by a :class:`compas.geometry.Box` and an optional fillet radius.

    The box is centred on the origin of its own frame and axis-aligned to it.

    Parameters
    ----------
    box : :class:`compas.geometry.Box`
        The base box.
    radius : float, optional
        The filleting radius along the edges. Default is ``0``.

    Examples
    --------
    >>> from compas.geometry import Box
    >>> from compas_vol.primitives import VolBox
    >>> box = Box(1.0, 2.0, 3.0)
    >>> vbx = VolBox(box, 0.3)
    >>> round(vbx.get_distance([0, 0, 0]), 6)
    -0.5
    """

    def __init__(self, box, radius=0.0, name=None):
        super().__init__(name=name)
        self._box = None
        self._radius = None
        self.inversetransform = None
        self.box = box
        self.radius = radius

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {"box": self.box.__data__, "radius": self.radius}

    @classmethod
    def __from_data__(cls, data):
        return cls(Box.__from_data__(data["box"]), data["radius"])

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def box(self):
        return self._box

    @box.setter
    def box(self, box):
        if not isinstance(box, Box):
            raise TypeError("Expected a compas.geometry.Box, got {}".format(type(box).__name__))
        self._box = box
        self.inversetransform = inverse_matrix_from_frame(box.frame)

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, radius):
        self._radius = max(float(radius), 0.0)

    @property
    def volume(self):
        if self.radius == 0:
            return self.box.volume
        xr = self.box.xsize - 2 * self.radius
        yr = self.box.ysize - 2 * self.radius
        zr = self.box.zsize - 2 * self.radius
        # box without the radius layer
        inner = xr * yr * zr
        # sides
        sides = Box(xr, yr, zr).area * self.radius
        # cylinder along all edges, base circle x height
        edges = (self.radius**2 * pi) * (xr + yr + zr)
        # eight times a corner, 1/8th of a sphere = 1 sphere
        corns = 4.0 / 3.0 * pi * self.radius**3
        return inner + sides + edges + corns

    def __repr__(self):
        return "VolBox({0!r}, {1})".format(self.box, format_number(self.radius))

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)

        dx = abs(p.x) - (self.box.xsize / 2.0 - self.radius)
        dy = abs(p.y) - (self.box.ysize / 2.0 - self.radius)
        dz = abs(p.z) - (self.box.zsize / 2.0 - self.radius)
        inside = max(dx, dy, dz) - self.radius
        if inside + self.radius < 0:
            return inside
        dx = max(dx, 0)
        dy = max(dy, 0)
        dz = max(dz, 0)
        return sqrt(dx * dx + dy * dy + dz * dz) - self.radius

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)

        dx = np.abs(xt) - (self.box.xsize / 2.0 - self.radius)
        dy = np.abs(yt) - (self.box.ysize / 2.0 - self.radius)
        dz = np.abs(zt) - (self.box.zsize / 2.0 - self.radius)
        inside = np.maximum(np.maximum(dx, dy), dz) - self.radius
        dx = np.maximum(dx, 0)
        dy = np.maximum(dy, 0)
        dz = np.maximum(dz, 0)
        corner = np.sqrt(dx**2 + dy**2 + dz**2) - self.radius
        return np.where(inside + self.radius < 0, inside, corner)
