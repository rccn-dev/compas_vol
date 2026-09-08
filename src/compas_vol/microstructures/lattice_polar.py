import math

from compas.geometry import Frame

from compas_vol.base import VolObject
from compas_vol.base import format_number
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy

from .lattice import LATTICE_TYPENAMES
from .lattice import create_points
from .lattice import create_types


class LatticePolar(VolObject):
    """A strut lattice tiled in cylindrical coordinates.

    Like :class:`Lattice`, but the cells repeat radially and around the Z axis
    instead of along X and Y, so the lattice wraps around a cylinder.

    Parameters
    ----------
    ltype : int
        The index of the lattice type. See :data:`compas_vol.microstructures.LATTICE_TYPENAMES`.
    unitcell : float
        The edge length of a unit cell.
    thickness : float
        The diameter of the struts.
    polarnumber : int
        The number of cells around the Z axis.
    frame : :class:`compas.geometry.Frame`, optional
        The base frame.

    Examples
    --------
    >>> from compas_vol.microstructures import LatticePolar
    >>> lat = LatticePolar(5, 5.0, 0.3, 6)
    >>> lat.lattice_type
    (5, 'octet')
    """

    def __init__(self, ltype=0, unitcell=1.0, thickness=0.1, polarnumber=6, frame=None, name=None):
        super().__init__(name=name)
        self.pointlist = create_points()
        self.ltypes = create_types()
        self._ltype = None
        self._frame = None
        self.inversetransform = None
        self.ltype = ltype
        self.unitcell = unitcell
        self.thickness = thickness
        self.polarnumber = polarnumber
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
            "polarnumber": self.polarnumber,
            "frame": self.frame.__data__,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(
            data["ltype"],
            data["unitcell"],
            data["thickness"],
            data["polarnumber"],
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
        return "LatticePolar({0},{1},{2},{3},{4!r})".format(
            self.ltype,
            format_number(self.unitcell),
            format_number(self.thickness),
            self.polarnumber,
            self.frame,
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

        radius = math.sqrt(p.x * p.x + p.y * p.y)
        polx = abs((radius % self.unitcell) - self.unitcell / 2)
        angle = (math.atan2(p.y, p.x) + math.pi) / (2 * math.pi)
        poly = abs(((angle * self.polarnumber) % 1 - 0.5) * self.unitcell)
        polz = abs((p.z % self.unitcell) - self.unitcell / 2)

        up = [polx, poly, polz]

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
        xt, yt, zt = (np.broadcast_to(c, shape) for c in (xt, yt, zt))

        radius = np.sqrt(xt**2 + yt**2)
        # The COMPAS 1 version left out the abs() on the radial coordinate that
        # its own single-point method applied, so the two disagreed.
        polx = np.abs((radius % self.unitcell) - self.unitcell / 2)
        angle = (np.arctan2(yt, xt) + math.pi) / (2 * math.pi)
        poly = np.abs(((angle * self.polarnumber) % 1 - 0.5) * self.unitcell)
        polz = np.abs((zt % self.unitcell) - self.unitcell / 2)
        mg = np.stack([polx, poly, polz], axis=-1)

        distances = []
        for sp, ep in self._struts():
            A = np.array(sp)
            B = np.array(ep)
            d = np.linalg.norm(np.cross(B - A, mg - A), axis=-1) / np.linalg.norm(B - A)
            distances.append(d)
        return np.asarray(distances).min(axis=0) - self.thickness / 2.0
