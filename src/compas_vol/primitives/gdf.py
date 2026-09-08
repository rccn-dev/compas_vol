from compas.geometry import Frame
from compas.geometry import Vector

from compas_vol.base import VolObject
from compas_vol.base import format_number
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy


def _unit(x, y, z):
    v = Vector(x, y, z)
    v.unitize()
    return (v.x, v.y, v.z)


_VA = 0.577
_VB = 0.357
_VC = 0.943
_VD = 0.851
_VE = 0.526

#: The symmetry directions used by the generalised distance functions.
GDFVECTORS = [
    _unit(1, 0, 0),
    _unit(0, 1, 0),
    _unit(0, 0, 1),
    _unit(_VA, _VA, _VA),
    _unit(-_VA, _VA, _VA),
    _unit(_VA, -_VA, _VA),
    _unit(_VA, _VA, -_VA),
    _unit(0, _VB, _VC),
    _unit(0, -_VB, _VC),
    _unit(_VC, 0, _VB),
    _unit(-_VC, 0, _VB),
    _unit(_VB, _VC, 0),
    _unit(-_VB, _VC, 0),
    _unit(0, _VD, _VE),
    _unit(0, -_VD, _VE),
    _unit(_VE, 0, _VD),
    _unit(-_VE, 0, _VD),
    _unit(_VD, _VE, 0),
    _unit(-_VD, _VE, 0),
]


class GDF(VolObject):
    """A generalised distance function for euclidean polyhedra.

    The solid is the intersection of half-spaces whose normals are a slice of
    :data:`GDFVECTORS`, which encodes the symmetry directions of the regular
    polyhedra. Selecting a range of those directions yields a different solid.

    In COMPAS 1 this class raised :exc:`NotImplementedError` from both distance
    methods and was commented out of the package exports; it is implemented here.

    Parameters
    ----------
    radius : float
        The circumradius of the solid.
    gdftype : str | tuple[int, int]
        Either a key of :attr:`RANGES`, or an explicit ``(start, end)`` slice
        into :data:`GDFVECTORS`.
    exponent : float, optional
        The blending exponent. ``None`` (the default) takes a hard maximum,
        giving flat faces. Finite values round the solid off.
    frame : :class:`compas.geometry.Frame`, optional
        The base frame. Defaults to the world XY frame.

    Examples
    --------
    >>> from compas_vol.primitives import GDF
    >>> g = GDF(10.0, "octahedron")
    >>> g.get_distance([0, 0, 0]) < 0
    True
    """

    RANGES = {
        "octahedron": (3, 7),
        "dodecahedron": (13, 19),
        "icosahedron": (3, 13),
        "truncated_octahedron": (0, 7),
        "truncated_icosahedron": (0, 13),
    }

    def __init__(self, radius=1.0, gdftype="octahedron", exponent=None, frame=None, name=None):
        super().__init__(name=name)
        self._frame = None
        self.inversetransform = None
        self.radius = radius
        self.gdftype = gdftype
        self.exponent = exponent
        self.frame = frame or Frame.worldXY()

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "radius": self.radius,
            "gdftype": self.gdftype,
            "exponent": self.exponent,
            "frame": self.frame.__data__,
        }

    @classmethod
    def __from_data__(cls, data):
        gdftype = data["gdftype"]
        if isinstance(gdftype, list):
            gdftype = tuple(gdftype)
        return cls(data["radius"], gdftype, data["exponent"], Frame.__from_data__(data["frame"]))

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
    def vectors(self):
        """The symmetry directions selected by :attr:`gdftype`."""
        if isinstance(self.gdftype, str):
            start, end = self.RANGES[self.gdftype]
        else:
            start, end = self.gdftype
        return GDFVECTORS[start:end]

    def __repr__(self):
        return "GDF({0},{1!r},{2},{3!r})".format(
            format_number(self.radius), self.gdftype, self.exponent, self.frame
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)

        projections = [abs(p.x * vx + p.y * vy + p.z * vz) for vx, vy, vz in self.vectors]
        if self.exponent is None:
            d = max(projections)
        else:
            d = sum(pr**self.exponent for pr in projections) ** (1.0 / self.exponent)
        return d - self.radius

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)

        projections = [np.abs(xt * vx + yt * vy + zt * vz) for vx, vy, vz in self.vectors]
        shape = np.broadcast_shapes(np.shape(xt), np.shape(yt), np.shape(zt))
        projections = [np.broadcast_to(pr, shape) for pr in projections]

        if self.exponent is None:
            d = np.maximum.reduce(projections)
        else:
            d = np.sum([pr**self.exponent for pr in projections], axis=0) ** (1.0 / self.exponent)
        return d - self.radius
