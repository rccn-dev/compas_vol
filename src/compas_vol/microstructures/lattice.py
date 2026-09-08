import math

from compas.geometry import Frame

from compas_vol.base import VolObject
from compas_vol.base import format_number
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy

#: Names of the available lattice types, indexed as in :attr:`Lattice.ltype`.
LATTICE_TYPENAMES = [
    "bigx",
    "grid",
    "star",
    "cross",
    "octagon",
    "octet",
    "vintile",
    "dual",
    "interlock",
    "isotrop",
    "hexgrid",
]


def create_points():
    """The 23 candidate strut anchors of a unit cell octant.

    The points sit on the vertices (0-7), the edge centres (8-19) and three
    offset positions (20-22) of the octant, in unit-cell fractions.
    """
    v1, v2, v3, v4 = 0.0, 0.5, 0.25, 0.20

    return [
        (v2, v1, v1),  # 0
        (v2, v2, v1),  # 1
        (v1, v1, v1),  # 2
        (v1, v2, v1),  # 3
        (v1, v1, v2),  # 4
        (v2, v1, v2),  # 5
        (v2, v2, v2),  # 6
        (v1, v2, v2),  # 7
        (v3, v1, v1),  # 8
        (v2, v3, v1),  # 9
        (v3, v2, v1),  # 10
        (v1, v3, v1),  # 11
        (v1, v1, v3),  # 12
        (v2, v1, v3),  # 13
        (v2, v2, v3),  # 14
        (v1, v2, v3),  # 15
        (v3, v1, v2),  # 16
        (v2, v3, v2),  # 17
        (v3, v2, v2),  # 18
        (v1, v3, v2),  # 19
        (v4, v1, v1),  # 20
        (v1, v4, v1),  # 21
        (v1, v1, v4),  # 22
    ]


def create_types():
    """The strut sets of each lattice type, as index pairs into :func:`create_points`."""
    bigx = [(0, 6)]
    grid = [(6, 2), (6, 5), (6, 7)]
    star = grid + bigx
    cross = [(1, 6), (3, 6), (4, 6)]
    octagon = [(1, 3), (3, 4), (4, 1)]
    octet = cross + octagon
    vintile = [(8, 13), (13, 17), (17, 18), (18, 15), (15, 11), (11, 8)]
    dual = [(0, 1), (0, 3), (0, 4)]
    interlock = grid + dual
    isotrop = [(0, 1), (2, 1), (5, 1), (7, 1), (3, 7), (6, 7), (4, 7)]
    hexgrid = [(6, 20), (6, 21), (6, 22)]

    return [bigx, grid, star, cross, octagon, octet, vintile, dual, interlock, isotrop, hexgrid]


class Lattice(VolObject):
    """A periodic strut lattice, defined by a type, a cell size and a strut diameter.

    Parameters
    ----------
    ltype : int
        The index of the lattice type. See :data:`LATTICE_TYPENAMES`.
    unitcell : float
        The edge length of a cubic unit cell.
    thickness : float
        The diameter of the struts.
    frame : :class:`compas.geometry.Frame`, optional
        The base frame, to reorient and reposition the lattice.

    Examples
    --------
    >>> from compas.geometry import Frame
    >>> from compas_vol.microstructures import Lattice
    >>> lat = Lattice(5, 5.0, 0.3)
    >>> lat.frame = Frame((1, 0, 0), (1, 0.2, 0.1), (-0.3, 1, 0.2))
    >>> lat.lattice_type
    (5, 'octet')
    """

    def __init__(self, ltype=0, unitcell=1.0, thickness=0.1, frame=None, name=None):
        super().__init__(name=name)
        self.pointlist = create_points()
        self.ltypes = create_types()
        self._ltype = None
        self._frame = None
        self.inversetransform = None
        self.ltype = ltype
        self.unitcell = unitcell
        self.thickness = thickness
        self.frame = frame or Frame.worldXY()

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "ltype": self.ltype,
            "unitcell": self.unitcell,
            "thickness": self.thickness,
            "frame": self.frame.__data__,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(
            data["ltype"], data["unitcell"], data["thickness"], Frame.__from_data__(data["frame"])
        )

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def frame(self):
        """:class:`compas.geometry.Frame`: The lattice's frame."""
        return self._frame

    @frame.setter
    def frame(self, frame):
        # COMPAS 1 rebuilt the frame with ``Frame(frame[0], frame[1], frame[2])``,
        # which relied on Frame being indexable. Accept a Frame directly, or a
        # (point, xaxis, yaxis) triple.
        if not isinstance(frame, Frame):
            frame = Frame(*frame)
        self._frame = frame
        self.inversetransform = inverse_matrix_from_frame(frame)

    @property
    def ltype(self):
        return self._ltype

    @ltype.setter
    def ltype(self, ltype):
        self._ltype = min(max(0, ltype), len(self.ltypes) - 1)

    @property
    def lattice_type(self):
        return self.ltype, self.typenames[self.ltype]

    @property
    def typenames(self):
        return dict(enumerate(LATTICE_TYPENAMES))

    def __repr__(self):
        return "Lattice({0},{1},{2},{3!r})".format(
            self.ltype, format_number(self.unitcell), format_number(self.thickness), self.frame
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def _struts(self):
        for ia, ib in self.ltypes[self.ltype]:
            a = [self.pointlist[ia][i] * self.unitcell for i in range(3)]
            b = [self.pointlist[ib][i] * self.unitcell for i in range(3)]
            yield a, b

    def get_distance(self, point):
        p = self._as_point(point)
        p.transform(self.inversetransform)

        up = [abs((c % self.unitcell) - self.unitcell / 2) for c in p]

        dmin = float("inf")
        for sp, ep in self._struts():
            v = [ep[i] - sp[i] for i in range(3)]
            d = [up[i] - sp[i] for i in range(3)]
            c2 = sum(i * i for i in v)
            c1 = sum(i * j for i, j in zip(d, v))
            b = c1 / c2
            q = [sp[i] + b * v[i] for i in range(3)]
            dmin = min(dmin, sum((up[i] - q[i]) ** 2 for i in range(3)))
        return math.sqrt(dmin) - self.thickness / 2.0

    def get_distance_numpy(self, x, y, z):
        import numpy as np

        xt, yt, zt = transform_numpy(self.inversetransform, x, y, z)
        shape = np.broadcast_shapes(np.shape(xt), np.shape(yt), np.shape(zt))
        mg = np.stack([np.broadcast_to(c, shape) for c in (xt, yt, zt)], axis=-1)
        mg = np.abs((mg % self.unitcell) - self.unitcell / 2)

        distances = []
        for sp, ep in self._struts():
            A = np.array(sp)
            B = np.array(ep)
            d = np.linalg.norm(np.cross(B - A, mg - A), axis=-1) / np.linalg.norm(B - A)
            distances.append(d)
        return np.asarray(distances).min(axis=0) - self.thickness / 2.0
