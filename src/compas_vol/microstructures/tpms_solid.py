from math import pi

from compas.geometry import Frame

from compas_vol.base import VolObject
from compas_vol.base import format_number
from compas_vol.base import inverse_matrix_from_frame
from compas_vol.base import transform_numpy

from .tpms import TPMSTYPES
from .tpms import resolve_tpmstype
from .tpms import tpms_field

#: The ways a TPMS can be turned into a solid.
TPMSMODES = ["sheet", "network"]

# Complex step for first derivatives, and real step for the second derivative
# along the normal, both in radians of phase (the fields have period 2 pi).
_H = 1e-20
_IH = 1j * _H
_S = 1e-4


class TPMSSolid(VolObject):
    """A printable TPMS solid, parametrized in model units.

    :class:`TPMS` evaluates the raw trigonometric field, whose values are not
    distances and whose zero set is a surface with no thickness. This class
    turns that surface into a solid a designer can dimension directly:

    * ``cell_size`` is the edge length of one unit cell, i.e. the true period.
    * ``thickness`` is the wall thickness in model units (``mode="sheet"``).
    * ``offset`` moves the surface, in model units, to one side or the other.
    * ``thickness`` and ``offset`` accept either a number or any volumetric
      object, whose field *value* at each point is used as the parameter.
      Combined with :class:`compas_vol.modifications.Remap`, that is how a wall
      is graded by an attractor, a plane, or any other field.

    The raw field is converted to an approximate distance by stepping to the
    surface along its normal with a second-order Taylor expansion. Measured
    along the normal, a gyroid wall comes out within about 2% of ``thickness``
    at a tenth of the cell size and about 6% at a fifth; the Schwarz P does
    better, the Neovius (whose channels are narrow) worse. The result can be combined with other
    volumetric objects like a metric field. It is still an approximation:
    far from the surface, values are only a bound on the true distance.

    Parameters
    ----------
    tpmstype : int | str
        The surface type. See :data:`compas_vol.microstructures.TPMSTYPES`.
    cell_size : float
        The edge length of a unit cell.
    thickness : float | :class:`compas_vol.base.VolObject`
        The wall thickness, used in ``"sheet"`` mode.
    mode : {"sheet", "network"}
        ``"sheet"`` thickens the surface into a wall, leaving two interwoven
        channel systems open (sometimes called a sheet-TPMS). ``"network"``
        fills one side of the surface, giving a solid network of rods
        (sometimes called a skeletal or solid-network TPMS).
    offset : float | :class:`compas_vol.base.VolObject`
        Shifts the surface along its normal. In ``"network"`` mode a positive
        offset grows the solid and so raises the volume fraction.
    invert : bool
        In ``"network"`` mode, fill the other side of the surface instead.
    frame : :class:`compas.geometry.Frame`, optional
        Orients and positions the lattice. Defaults to the world XY frame.

    Examples
    --------
    >>> from compas_vol.microstructures import TPMSSolid
    >>> g = TPMSSolid("Gyroid", cell_size=10.0, thickness=1.0)
    >>> round(g.get_distance([0, 0, 0]), 6)  # the origin lies on the gyroid
    -0.5
    """

    def __init__(
        self,
        tpmstype=0,
        cell_size=10.0,
        thickness=1.0,
        mode="sheet",
        offset=0.0,
        invert=False,
        frame=None,
        name=None,
    ):
        super().__init__(name=name)
        self._tpmstype = None
        self._cell_size = None
        self._mode = None
        self._frame = None
        self.tpmstype = tpmstype
        self.cell_size = cell_size
        self.thickness = thickness
        self.mode = mode
        self.offset = offset
        self.invert = bool(invert)
        self.frame = frame

    # ==========================================================================
    # data
    # ==========================================================================

    @property
    def __data__(self):
        return {
            "tpmstype": self.tpmstype,
            "cell_size": self.cell_size,
            "thickness": self.thickness,
            "mode": self.mode,
            "offset": self.offset,
            "invert": self.invert,
            "frame": self.frame,
        }

    @classmethod
    def __from_data__(cls, data):
        return cls(
            data["tpmstype"],
            data["cell_size"],
            data["thickness"],
            data["mode"],
            data["offset"],
            data["invert"],
            data["frame"],
        )

    # ==========================================================================
    # descriptors
    # ==========================================================================

    @property
    def tpmstype(self):
        return self._tpmstype

    @tpmstype.setter
    def tpmstype(self, tpmstype):
        self._tpmstype = resolve_tpmstype(tpmstype)

    @property
    def typename(self):
        return TPMSTYPES[self.tpmstype]

    @property
    def cell_size(self):
        """float: The edge length of one unit cell."""
        return self._cell_size

    @cell_size.setter
    def cell_size(self, cell_size):
        cell_size = float(cell_size)
        if cell_size <= 0:
            raise ValueError("cell_size must be positive, got {}".format(cell_size))
        self._cell_size = cell_size

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode):
        if mode not in TPMSMODES:
            raise ValueError("mode must be one of {}, got {!r}".format(TPMSMODES, mode))
        self._mode = mode

    @property
    def frame(self):
        """:class:`compas.geometry.Frame` | None: The frame the lattice is aligned to."""
        return self._frame

    @frame.setter
    def frame(self, frame):
        if frame is not None and not isinstance(frame, Frame):
            raise TypeError("Expected a compas.geometry.Frame or None, got {}".format(type(frame).__name__))
        self._frame = frame
        self._inverse = inverse_matrix_from_frame(frame) if frame is not None else None

    def __repr__(self):
        return "TPMSSolid({0!r},{1},{2},{3!r},{4},{5},{6!r})".format(
            self.typename,
            format_number(self.cell_size),
            _format_parameter(self.thickness),
            self.mode,
            _format_parameter(self.offset),
            self.invert,
            self.frame,
        )

    # ==========================================================================
    # distance functions
    # ==========================================================================

    def normalized_field(self, x, y, z):
        """The approximate signed distance to the zero-thickness surface.

        Works on floats and on broadcastable arrays alike.

        Parameters
        ----------
        x, y, z : float | :class:`numpy.ndarray`
            World coordinates.

        Returns
        -------
        float | :class:`numpy.ndarray`
        """
        import numpy as np

        if self._inverse is not None:
            x, y, z = transform_numpy(self._inverse, x, y, z)

        k = 2 * pi / self.cell_size
        u, v, w = k * x, k * y, k * z
        t = self.tpmstype

        # Derivatives by complex step: F(p + i h e) has imaginary part h dF/de
        # to machine precision, with none of the cancellation a finite
        # difference suffers. The fields are built from numpy sin/cos, which
        # accept complex input.
        f = tpms_field(t, u, v, w)
        gu = tpms_field(t, u + _IH, v, w).imag / _H
        gv = tpms_field(t, u, v + _IH, w).imag / _H
        gw = tpms_field(t, u, v, w + _IH).imag / _H
        g = np.maximum(np.sqrt(gu * gu + gv * gv + gw * gw), 1e-12)
        nu, nv, nw = gu / g, gv / g, gw / g

        # Second derivative along the normal: a central difference of the
        # complex-step directional derivative.
        def directional(s):
            return tpms_field(t, u + (s + _IH) * nu, v + (s + _IH) * nv, w + (s + _IH) * nw).imag / _H

        fnn = (directional(_S) - directional(-_S)) / (2 * _S)

        # Solve F + g s + fnn s^2 / 2 = 0 for the step s to the surface along
        # the normal, taking the root nearest zero in its stable form. The
        # plain first-order estimate F / g overstates thick walls on curved
        # cells by up to ~20%; the quadratic keeps them within a few percent.
        discriminant = np.maximum(g * g - 2 * fnn * f, 0.0)
        d = 2 * f / (g + np.sqrt(discriminant))

        # Phase units to model units. At the critical points of F, far from the
        # surface, the gradient vanishes; no point is further than half a cell
        # from the surface, so clamping keeps the field finite there.
        half = self.cell_size / 2
        return np.clip(d / k, -half, half)

    def _solid(self, d, thickness, offset):
        import numpy as np

        if self.mode == "sheet":
            return np.abs(d - offset) - thickness / 2.0
        if self.invert:
            return -d - offset
        return d - offset

    def get_distance(self, point):
        x, y, z = point
        d = float(self.normalized_field(float(x), float(y), float(z)))
        thickness = _parameter_at_point(self.thickness, point)
        offset = _parameter_at_point(self.offset, point)
        return float(self._solid(d, thickness, offset))

    def get_distance_numpy(self, x, y, z):
        d = self.normalized_field(x, y, z)
        thickness = _parameter_on_grid(self.thickness, x, y, z)
        offset = _parameter_on_grid(self.offset, x, y, z)
        return self._solid(d, thickness, offset)


# ==============================================================================
# parameters that may be numbers or fields
# ==============================================================================


def _parameter_at_point(value, point):
    if isinstance(value, VolObject):
        return value.get_distance(point)
    return float(value)


def _parameter_on_grid(value, x, y, z):
    if isinstance(value, VolObject):
        return value.get_distance_numpy(x, y, z)
    return float(value)


def _format_parameter(value):
    if isinstance(value, VolObject):
        return repr(value)
    return format_number(value)
